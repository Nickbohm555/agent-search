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
from schemas import AgentRunStageMetadata, RuntimeAgentRunResponse, SubQuestionAnswer


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


def test_run_async_signature_requires_query_vector_store_and_model() -> None:
    signature = inspect.signature(public_api.run_async)
    assert str(signature) == "(query: 'str', *, vector_store: 'Any', model: 'Any', config: 'dict[str, Any] | None' = None) -> 'RuntimeAgentRunAsyncStartResponse'"
    assert signature.parameters["query"].default is inspect._empty
    assert signature.parameters["vector_store"].default is inspect._empty
    assert signature.parameters["model"].default is inspect._empty


def test_run_async_returns_job_start_shape(monkeypatch) -> None:
    def fake_start_agent_run_job(payload):
        assert payload.query == "Show me async flow"
        return SimpleNamespace(job_id="job-123", run_id="run-123", status="running")

    monkeypatch.setattr(public_api, "start_agent_run_job", fake_start_agent_run_job)

    response = public_api.run_async("Show me async flow", vector_store=_CompatibleVectorStore(), model=object())

    assert response.model_dump() == {
        "job_id": "job-123",
        "run_id": "run-123",
        "status": "running",
    }


def test_get_run_status_returns_runtime_status_shape_with_timing(monkeypatch) -> None:
    def fake_get_agent_run_job(job_id):
        assert job_id == "job-456"
        return SimpleNamespace(
            job_id="job-456",
            run_id="run-456",
            status="completed",
            message="Run completed.",
            stage="completed",
            stages=[
                AgentRunStageMetadata(
                    stage="subquestions_ready",
                    status="completed",
                    sub_question="",
                    lane_index=0,
                    lane_total=2,
                    emitted_at=123.0,
                )
            ],
            decomposition_sub_questions=["What is NATO?"],
            sub_question_artifacts=[],
            sub_qa=[SubQuestionAnswer(sub_question="What is NATO?", sub_answer="An alliance.")],
            output="NATO is an alliance.",
            result=RuntimeAgentRunResponse(
                main_question="What is NATO?",
                sub_qa=[SubQuestionAnswer(sub_question="What is NATO?", sub_answer="An alliance.")],
                output="NATO is an alliance.",
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
    assert payload["status"] == "completed"
    assert payload["stage"] == "completed"
    assert payload["elapsed_ms"] == 1500
    assert payload["result"]["main_question"] == "What is NATO?"
    assert payload["result"]["output"] == "NATO is an alliance."


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
