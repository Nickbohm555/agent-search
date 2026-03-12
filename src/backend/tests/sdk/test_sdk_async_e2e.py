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
from agent_search.runtime import runner as runtime_runner
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

    def fake_execute_runtime_graph(*, context, run_metadata, config=None):
        assert config is None
        captured["run_query"] = context.payload.query
        captured["payload_thread_id"] = context.payload.thread_id
        captured["run_vector_store"] = context.vector_store
        captured["run_model"] = context.model
        captured["run_thread_id"] = run_metadata.thread_id
        captured["initial_search_context"] = context.initial_search_context
        return {
            "main_question": "How does SDK async wiring work?",
            "decomposition_sub_questions": ["What is the key fact?"],
            "sub_question_artifacts": [],
            "final_answer": "Final async answer with citation [1].",
            "citation_rows_by_index": {},
            "run_metadata": run_metadata,
            "sub_qa": [
                SubQuestionAnswer(
                    sub_question="What is the key fact?",
                    sub_answer="The key fact is captured with citation [1].",
                )
            ],
            "output": "Final async answer with citation [1].",
            "stage_snapshots": [
                GraphStageSnapshot(
                    stage="decompose",
                    status="completed",
                    decomposition_sub_questions=["What is the key fact?"],
                    output="Snapshot output",
                )
            ],
        }

    monkeypatch.setattr(runtime_jobs, "execute_runtime_graph", fake_execute_runtime_graph)
    monkeypatch.setattr(
        runtime_runner.legacy_service,
        "run_parallel_graph_runner",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("legacy async runner should not execute")),
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

    monkeypatch.setattr(runtime_jobs, "_EXECUTOR", _InlineExecutor())

    def fake_run_checkpointed_agent(*, payload, run_metadata, resume=None, **_kwargs):
        captured.append((payload.query, resume))
        return SimpleNamespace(
            status="completed",
            state={
                "main_question": payload.query,
                "decomposition_sub_questions": ["What changed?"],
                "sub_question_artifacts": [],
                "final_answer": "The checkpoint resumed.",
                "citation_rows_by_index": {},
                "run_metadata": run_metadata,
                "sub_qa": [SubQuestionAnswer(sub_question="What changed?", sub_answer="The checkpoint resumed.")],
                "output": "The checkpoint resumed.",
                "stage_snapshots": [],
            },
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
    with runtime_jobs._JOB_LOCK:
        runtime_jobs._JOBS["job-resume"] = runtime_jobs.AgentRunJobStatus(
            job_id="job-resume",
            run_id="job-resume",
            thread_id=thread_id,
            status="paused",
            query="Resume this run",
            message="Paused and awaiting resume input.",
            stage="paused",
            interrupt_payload={"kind": "approval", "question": "Approve resume?"},
            checkpoint_id="checkpoint-1",
            runtime_model=sentinel_model,
            runtime_vector_store=sentinel_vector_store,
        )

    paused_status = public_api.get_run_status("job-resume")
    resumed_status = public_api.resume_run("job-resume", resume={"approved": True})

    assert paused_status.status == "paused"
    assert paused_status.thread_id == thread_id
    assert paused_status.message == "Paused and awaiting resume input."
    assert paused_status.stage == "paused"
    assert resumed_status.status == "success"
    assert resumed_status.thread_id == thread_id
    assert resumed_status.result is not None
    assert resumed_status.result.output == "The checkpoint resumed."
    assert captured == [("Resume this run", {"approved": True})]


def test_sdk_async_resume_rejects_invalid_transition_deterministically(monkeypatch) -> None:
    thread_id = "550e8400-e29b-41d4-a716-446655440011"

    with runtime_jobs._JOB_LOCK:
        runtime_jobs._JOBS["job-finished"] = runtime_jobs.AgentRunJobStatus(
            job_id="job-finished",
            run_id="job-finished",
            thread_id=thread_id,
            status="success",
            query="Finish this run",
            message="Completed.",
            stage="completed",
            runtime_model=object(),
            runtime_vector_store=_CompatibleVectorStore(),
            result=RuntimeAgentRunResponse(main_question="Done", thread_id=thread_id, output="Done"),
        )

    with pytest.raises(SDKConfigurationError, match="Run cannot be resumed from status 'success'."):
        public_api.resume_run("job-finished")


@pytest.mark.parametrize("initial_status", ["running", "error", "cancelled"])
def test_sdk_async_resume_rejects_non_paused_transition_matrix(monkeypatch, initial_status: str) -> None:
    monkeypatch.setattr(
        public_api,
        "resume_agent_run_job",
        lambda _job_id, resume=True: (_ for _ in ()).throw(
            SDKConfigurationError(f"Run cannot be resumed from status '{initial_status}'.")
        ),
    )

    with pytest.raises(SDKConfigurationError, match=rf"Run cannot be resumed from status '{initial_status}'\."):
        public_api.resume_run("job-transition-matrix", resume={"approved": True})


def test_sdk_async_resume_status_preserves_thread_id_after_checkpoint_resume(monkeypatch) -> None:
    thread_id = "550e8400-e29b-41d4-a716-446655440013"

    def fake_resume_agent_run_job(_job_id: str, *, resume=True):
        assert resume == {"approved": True}
        return runtime_jobs.AgentRunJobStatus(
            job_id="job-resume-status",
            run_id="run-resume-status",
            thread_id=thread_id,
            status="success",
            query="Resume and report status",
            message="Completed.",
            stage="completed",
            result=RuntimeAgentRunResponse(
                main_question="Resume and report status",
                thread_id=thread_id,
                sub_qa=[],
                output="Recovered from checkpoint.",
            ),
        )

    monkeypatch.setattr(public_api, "resume_agent_run_job", fake_resume_agent_run_job)
    monkeypatch.setattr(public_api, "get_agent_run_job", lambda _job_id: fake_resume_agent_run_job(_job_id, resume={"approved": True}))

    resumed_status = public_api.resume_run("job-resume-status", resume={"approved": True})

    assert resumed_status.job_id == "job-resume-status"
    assert resumed_status.run_id == "run-resume-status"
    assert resumed_status.thread_id == thread_id
    assert resumed_status.status == "success"
    assert resumed_status.result is not None
    assert resumed_status.result.thread_id == thread_id
    assert resumed_status.result.output == "Recovered from checkpoint."
