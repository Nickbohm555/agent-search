from __future__ import annotations

import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from agent_search.errors import SDKConfigurationError
from agent_search.runtime import jobs as runtime_jobs
from agent_search.runtime import runner as runtime_runner
from schemas import AgentRunStageMetadata, CitationSourceRow, GraphStageSnapshot, RuntimeAgentRunResponse, SubQuestionAnswer
from services import agent_service


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


class _InlineExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)

        class _CompletedFuture:
            def result(self):
                return None

        return _CompletedFuture()


def test_run_async_signature_requires_query_vector_store_and_model() -> None:
    signature = inspect.signature(public_api.run_async)
    assert str(signature) == "(query: 'str', *, vector_store: 'Any', model: 'Any', config: 'dict[str, Any] | None' = None) -> 'RuntimeAgentRunAsyncStartResponse'"
    assert signature.parameters["query"].default is inspect._empty
    assert signature.parameters["vector_store"].default is inspect._empty
    assert signature.parameters["model"].default is inspect._empty


def test_run_async_returns_job_start_shape(monkeypatch) -> None:
    def fake_start_agent_run_job(payload, **kwargs):
        assert payload.query == "Show me async flow"
        assert payload.thread_id == "550e8400-e29b-41d4-a716-446655440000"
        assert "model" in kwargs
        assert "vector_store" in kwargs
        return SimpleNamespace(
            job_id="job-123",
            run_id="run-123",
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            status="running",
        )

    monkeypatch.setattr(public_api, "start_agent_run_job", fake_start_agent_run_job)

    response = public_api.run_async(
        "Show me async flow",
        vector_store=_CompatibleVectorStore(),
        model=object(),
        config={"thread_id": "550e8400-e29b-41d4-a716-446655440000"},
    )

    assert response.model_dump() == {
        "job_id": "job-123",
        "run_id": "run-123",
        "thread_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "running",
    }


def test_run_async_returns_server_generated_thread_id_when_config_omits_it(monkeypatch) -> None:
    generated_thread_id = "550e8400-e29b-41d4-a716-446655440111"

    def fake_start_agent_run_job(payload, **kwargs):
        assert payload.query == "Show me async flow"
        assert payload.thread_id is None
        assert "model" in kwargs
        assert "vector_store" in kwargs
        return SimpleNamespace(
            job_id="job-456",
            run_id="run-456",
            thread_id=generated_thread_id,
            status="running",
        )

    monkeypatch.setattr(public_api, "start_agent_run_job", fake_start_agent_run_job)

    response = public_api.run_async(
        "Show me async flow",
        vector_store=_CompatibleVectorStore(),
        model=object(),
    )

    assert response.model_dump() == {
        "job_id": "job-456",
        "run_id": "run-456",
        "thread_id": generated_thread_id,
        "status": "running",
    }


def test_run_async_and_status_share_same_thread_id_for_one_run_lineage(monkeypatch) -> None:
    thread_id = "550e8400-e29b-41d4-a716-446655440001"

    monkeypatch.setattr(
        public_api,
        "start_agent_run_job",
        lambda payload, **kwargs: SimpleNamespace(
            job_id="job-789",
            run_id="run-789",
            thread_id=thread_id,
            status="running",
        ),
    )
    monkeypatch.setattr(
        public_api,
        "get_agent_run_job",
        lambda _job_id: SimpleNamespace(
            job_id="job-789",
            run_id="run-789",
            thread_id=thread_id,
            status="running",
            message="Still running.",
            stage="running",
            stages=[],
            decomposition_sub_questions=[],
            sub_question_artifacts=[],
            sub_qa=[],
            output="",
            result=None,
            error=None,
            cancel_requested=False,
            started_at=None,
            finished_at=None,
        ),
    )

    start_response = public_api.run_async(
        "Track continuity",
        vector_store=_CompatibleVectorStore(),
        model=object(),
    )
    status_response = public_api.get_run_status("job-789")

    assert start_response.thread_id == thread_id
    assert status_response.thread_id == thread_id


def test_get_run_status_returns_runtime_status_shape_with_timing(monkeypatch) -> None:
    def fake_get_agent_run_job(job_id):
        assert job_id == "job-456"
        return SimpleNamespace(
            job_id="job-456",
            run_id="run-456",
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            status="completed",
            message="Run completed.",
            stage="completed",
            stages=[
                AgentRunStageMetadata(
                    stage="subquestions_ready",
                    status="completed",
                    sub_question="",
                    lane_index=0,
                    lane_total=1,
                    emitted_at=123.0,
                ),
                AgentRunStageMetadata(
                    stage="synthesize",
                    status="completed",
                    sub_question="What is NATO?",
                    lane_index=1,
                    lane_total=1,
                    emitted_at=124.5,
                )
            ],
            decomposition_sub_questions=["What is NATO?"],
            sub_question_artifacts=[],
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="What is NATO?",
                    sub_answer="An alliance.",
                    expanded_query="What is NATO and how is it structured?",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                )
            ],
            output="NATO is an alliance. [1]",
            result=RuntimeAgentRunResponse(
                main_question="What is NATO?",
                thread_id="550e8400-e29b-41d4-a716-446655440000",
                sub_qa=[
                    SubQuestionAnswer(
                        sub_question="What is NATO?",
                        sub_answer="An alliance.",
                        expanded_query="What is NATO and how is it structured?",
                        answerable=True,
                        verification_reason="grounded_in_reranked_documents",
                    )
                ],
                output="NATO is an alliance. [1]",
                final_citations=[
                    CitationSourceRow(
                        citation_index=1,
                        rank=1,
                        title="NATO reference",
                        source="docs://nato",
                        content="NATO is a political and military alliance.",
                        document_id="doc-nato",
                        score=0.97,
                    )
                ],
            ),
            error=None,
            cancel_requested=False,
            started_at=100.0,
            finished_at=101.5,
        )

    monkeypatch.setattr(public_api, "get_agent_run_job", fake_get_agent_run_job)

    response = public_api.get_run_status("job-456")
    payload = response.model_dump()
    assert payload["job_id"] == "job-456"
    assert payload["run_id"] == "run-456"
    assert payload["thread_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert payload["status"] == "completed"
    assert payload["stage"] == "completed"
    assert payload["elapsed_ms"] == 1500
    assert [stage["stage"] for stage in payload["stages"]] == ["subquestions_ready", "synthesize"]
    assert payload["sub_qa"][0]["answerable"] is True
    assert payload["sub_qa"][0]["verification_reason"] == "grounded_in_reranked_documents"
    assert payload["result"]["main_question"] == "What is NATO?"
    assert payload["result"]["thread_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert payload["result"]["output"] == "NATO is an alliance. [1]"
    assert payload["result"]["final_citations"][0]["citation_index"] == 1
    assert payload["result"]["final_citations"][0]["title"] == "NATO reference"


def test_cancel_run_returns_success_shape(monkeypatch) -> None:
    monkeypatch.setattr(public_api, "cancel_agent_run_job", lambda _job_id: True)

    response = public_api.cancel_run("job-123")

    assert response.model_dump() == {"status": "success", "message": "Cancellation requested."}


def test_get_run_status_raises_configuration_error_for_missing_job(monkeypatch) -> None:
    monkeypatch.setattr(public_api, "get_agent_run_job", lambda _job_id: None)

    try:
        public_api.get_run_status("missing-job")
    except SDKConfigurationError as exc:
        assert str(exc) == "Job not found."
    else:
        raise AssertionError("Expected SDKConfigurationError for missing job")


def test_cancel_run_raises_configuration_error_when_not_found_or_finished(monkeypatch) -> None:
    monkeypatch.setattr(public_api, "cancel_agent_run_job", lambda _job_id: False)

    try:
        public_api.cancel_run("missing-job")
    except SDKConfigurationError as exc:
        assert str(exc) == "Job not found or already finished."
    else:
        raise AssertionError("Expected SDKConfigurationError for uncancellable job")


def test_run_async_rejects_invalid_thread_id_format(monkeypatch) -> None:
    monkeypatch.setattr(public_api, "start_agent_run_job", lambda *args, **kwargs: None)

    try:
        public_api.run_async(
            "Bad thread id",
            vector_store=_CompatibleVectorStore(),
            model=object(),
            config={"thread_id": "not-a-uuid"},
        )
    except SDKConfigurationError as exc:
        assert str(exc) == "run_async failed due to invalid SDK input or configuration."
    else:
        raise AssertionError("Expected SDKConfigurationError for invalid thread_id")


def test_run_async_cutover_blocks_legacy_orchestration(monkeypatch) -> None:
    sentinel_model = object()
    sentinel_vector_store = _CompatibleVectorStore()
    thread_id = "550e8400-e29b-41d4-a716-446655440123"
    captured: dict[str, object] = {}

    monkeypatch.setattr(runtime_jobs.uuid, "uuid4", lambda: "job-cutover")
    monkeypatch.setattr(runtime_jobs, "_persist_job_status", lambda _job: None)
    monkeypatch.setattr(runtime_jobs, "_EXECUTOR", _InlineExecutor())

    def fake_execute_runtime_graph(*, context, run_metadata, config=None, lifecycle_callback=None):
        captured["query"] = context.payload.query
        captured["payload_thread_id"] = context.payload.thread_id
        captured["vector_store"] = context.vector_store
        captured["model"] = context.model
        captured["run_thread_id"] = run_metadata.thread_id
        captured["config"] = config
        captured["lifecycle_callback"] = lifecycle_callback
        return {
            "main_question": context.payload.query,
            "decomposition_sub_questions": ["Which runtime completed the request?"],
            "sub_question_artifacts": [],
            "final_answer": "The LangGraph async runtime path completed the request.",
            "citation_rows_by_index": {},
            "run_metadata": run_metadata,
            "sub_qa": [
                SubQuestionAnswer(
                    sub_question="Which runtime completed the request?",
                    sub_answer="The LangGraph async runtime path completed the request.",
                )
            ],
            "output": "The LangGraph async runtime path completed the request.",
            "stage_snapshots": [
                GraphStageSnapshot(
                    stage="decompose",
                    status="completed",
                    decomposition_sub_questions=["Which runtime completed the request?"],
                    output="The LangGraph async runtime path completed the request.",
                )
            ],
        }

    monkeypatch.setattr(runtime_jobs, "execute_runtime_graph", fake_execute_runtime_graph)
    monkeypatch.setattr(
        runtime_jobs,
        "run_checkpointed_agent",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("checkpointed legacy orchestration should not execute")),
    )
    monkeypatch.setattr(
        runtime_runner.legacy_service,
        "run_parallel_graph_runner",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("legacy orchestration should not execute")),
    )

    with runtime_jobs._JOB_LOCK:
        runtime_jobs._JOBS.clear()

    start_response = public_api.run_async(
        "Which runtime completed the request?",
        vector_store=sentinel_vector_store,
        model=sentinel_model,
        config={"thread_id": thread_id},
    )
    status_response = public_api.get_run_status(start_response.job_id)

    assert start_response.model_dump() == {
        "job_id": "job-cutover",
        "run_id": "job-cutover",
        "thread_id": thread_id,
        "status": "success",
    }
    assert status_response.status == "success"
    assert status_response.thread_id == thread_id
    assert status_response.result is not None
    assert status_response.result.output == "The LangGraph async runtime path completed the request."
    assert captured == {
        "query": "Which runtime completed the request?",
        "payload_thread_id": thread_id,
        "vector_store": sentinel_vector_store,
        "model": sentinel_model,
        "run_thread_id": thread_id,
        "config": None,
        "lifecycle_callback": captured["lifecycle_callback"],
    }
