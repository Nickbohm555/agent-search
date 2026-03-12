from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from agent_search.errors import SDKConfigurationError
from agent_search.runtime import jobs as runtime_jobs
from schemas import GraphStageSnapshot, RuntimeAgentRunResponse, SubQuestionAnswer


class _InlineExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)

        class _CompletedFuture:
            def result(self):
                return None

        return _CompletedFuture()


class _NoopExecutor:
    def submit(self, fn, *args, **kwargs):
        class _PendingFuture:
            def result(self):
                return None

        return _PendingFuture()


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


@pytest.fixture(autouse=True)
def clear_runtime_jobs(monkeypatch):
    monkeypatch.setattr(runtime_jobs, "_persist_job_status", lambda _job: None)
    with runtime_jobs._JOB_LOCK:
        runtime_jobs._JOBS.clear()
    yield
    with runtime_jobs._JOB_LOCK:
        runtime_jobs._JOBS.clear()


def test_sdk_async_run_e2e_uses_runtime_job_manager_with_caller_dependencies(monkeypatch) -> None:
    sentinel_model = object()
    sentinel_vector_store = _CompatibleVectorStore()
    captured: dict[str, object] = {}
    thread_id = "550e8400-e29b-41d4-a716-446655440000"

    monkeypatch.setattr(runtime_jobs.uuid, "uuid4", lambda: "job-inline")
    monkeypatch.setattr(runtime_jobs, "_EXECUTOR", _InlineExecutor())

    def fake_run_parallel_graph_runner(*, payload, vector_store, model, run_metadata, initial_search_context, snapshot_callback):
        captured["run_query"] = payload.query
        captured["payload_thread_id"] = payload.thread_id
        captured["run_vector_store"] = vector_store
        captured["run_model"] = model
        captured["run_thread_id"] = run_metadata.thread_id
        captured["initial_search_context"] = initial_search_context
        snapshot_callback(
            GraphStageSnapshot(
                stage="decompose",
                status="completed",
                decomposition_sub_questions=["What is the key fact?"],
                output="Snapshot output",
            ),
            object(),
        )
        return type(
            "FakeState",
            (),
            {
                "decomposition_sub_questions": ["What is the key fact?"],
                "sub_question_artifacts": [],
            },
        )()

    monkeypatch.setattr(runtime_jobs, "run_parallel_graph_runner", fake_run_parallel_graph_runner)
    monkeypatch.setattr(
        runtime_jobs,
        "map_graph_state_to_runtime_response",
        lambda _state: RuntimeAgentRunResponse(
            main_question="How does SDK async wiring work?",
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="What is the key fact?",
                    sub_answer="The key fact is captured with citation [1].",
                )
            ],
            output="Final async answer with citation [1].",
        ),
    )

    start_response = public_api.run_async(
        "How does SDK async wiring work?",
        model=sentinel_model,
        vector_store=sentinel_vector_store,
        config={"thread_id": thread_id},
    )
    status_response = public_api.get_run_status(start_response.job_id)

    assert start_response.model_dump() == {
        "job_id": "job-inline",
        "run_id": "job-inline",
        "thread_id": thread_id,
        "status": "success",
    }
    assert status_response.status == "success"
    assert status_response.thread_id == thread_id
    assert status_response.stage == "subquestions_ready"
    assert status_response.result is not None
    assert status_response.result.output == "Final async answer with citation [1]."
    assert status_response.decomposition_sub_questions == ["What is the key fact?"]
    assert status_response.stages[0].stage == "subquestions_ready"
    assert captured == {
        "run_query": "How does SDK async wiring work?",
        "payload_thread_id": thread_id,
        "run_vector_store": sentinel_vector_store,
        "run_model": sentinel_model,
        "run_thread_id": thread_id,
        "initial_search_context": [],
    }


def test_sdk_async_cancel_e2e_preserves_cancellation_semantics(monkeypatch) -> None:
    monkeypatch.setattr(runtime_jobs.uuid, "uuid4", lambda: "job-cancel")
    monkeypatch.setattr(runtime_jobs, "_EXECUTOR", _NoopExecutor())
    thread_id = "550e8400-e29b-41d4-a716-446655440001"

    start_response = public_api.run_async(
        "Cancel this async run",
        model=object(),
        vector_store=_CompatibleVectorStore(),
        config={"thread_id": thread_id},
    )
    cancel_response = public_api.cancel_run(start_response.job_id)
    status_response = public_api.get_run_status(start_response.job_id)

    assert cancel_response.model_dump() == {"status": "success", "message": "Cancellation requested."}
    assert start_response.thread_id == thread_id
    assert status_response.thread_id == thread_id
    assert status_response.status == "cancelling"
    assert status_response.cancel_requested is True
    assert status_response.message == "Cancellation requested."


def test_sdk_async_resume_e2e_reuses_thread_id_after_interrupt(monkeypatch) -> None:
    thread_id = "550e8400-e29b-41d4-a716-446655440010"
    sentinel_model = object()
    sentinel_vector_store = _CompatibleVectorStore()
    captured: list[tuple[str, object | None]] = []

    monkeypatch.setattr(runtime_jobs.uuid, "uuid4", lambda: "job-resume")
    monkeypatch.setattr(runtime_jobs, "_EXECUTOR", _InlineExecutor())

    def fake_run_checkpointed_agent(*, payload, run_metadata, resume=None, **_kwargs):
        captured.append((payload.query, resume))
        if resume is None:
            return SimpleNamespace(
                status="paused",
                state=None,
                response=None,
                interrupt_payload={"kind": "approval", "question": "Approve resume?"},
                checkpoint_id="checkpoint-1",
            )
        return SimpleNamespace(
            status="completed",
            state=type(
                "FakeState",
                (),
                {
                    "decomposition_sub_questions": ["What changed?"],
                    "sub_question_artifacts": [],
                    "stage_snapshots": [],
                    "run_metadata": run_metadata,
                },
            )(),
            response=RuntimeAgentRunResponse(
                main_question=payload.query,
                thread_id=thread_id,
                sub_qa=[SubQuestionAnswer(sub_question="What changed?", sub_answer="The checkpoint resumed.")],
                output="The checkpoint resumed.",
            ),
            interrupt_payload=None,
            checkpoint_id="checkpoint-2",
        )

    monkeypatch.setattr(runtime_jobs, "run_checkpointed_agent", fake_run_checkpointed_agent)

    start_response = public_api.run_async(
        "Resume this run",
        model=sentinel_model,
        vector_store=sentinel_vector_store,
        config={"thread_id": thread_id},
    )
    paused_status = public_api.get_run_status(start_response.job_id)
    resumed_status = public_api.resume_run(start_response.job_id, resume={"approved": True})

    assert start_response.thread_id == thread_id
    assert paused_status.status == "paused"
    assert paused_status.thread_id == thread_id
    assert paused_status.message == "Paused and awaiting resume input."
    assert paused_status.stage == "paused"
    assert resumed_status.status == "success"
    assert resumed_status.thread_id == thread_id
    assert resumed_status.result is not None
    assert resumed_status.result.output == "The checkpoint resumed."
    assert captured == [
        ("Resume this run", None),
        ("Resume this run", {"approved": True}),
    ]


def test_sdk_async_resume_rejects_invalid_transition_deterministically(monkeypatch) -> None:
    thread_id = "550e8400-e29b-41d4-a716-446655440011"

    monkeypatch.setattr(runtime_jobs.uuid, "uuid4", lambda: "job-finished")
    monkeypatch.setattr(runtime_jobs, "_EXECUTOR", _InlineExecutor())
    monkeypatch.setattr(
        runtime_jobs,
        "run_checkpointed_agent",
        lambda **_kwargs: SimpleNamespace(
            status="completed",
            state=type(
                "FakeState",
                (),
                {
                    "decomposition_sub_questions": [],
                    "sub_question_artifacts": [],
                    "stage_snapshots": [],
                },
            )(),
            response=RuntimeAgentRunResponse(main_question="Done", thread_id=thread_id, output="Done"),
            checkpoint_id="checkpoint-final",
        ),
    )

    start_response = public_api.run_async(
        "Finish this run",
        model=object(),
        vector_store=_CompatibleVectorStore(),
        config={"thread_id": thread_id},
    )

    with pytest.raises(SDKConfigurationError, match="Run cannot be resumed from status 'success'."):
        public_api.resume_run(start_response.job_id)
