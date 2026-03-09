from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schemas import (
    RuntimeAgentRunAsyncCancelResponse,
    RuntimeAgentRunAsyncStartResponse,
    RuntimeAgentRunAsyncStatusResponse,
    RuntimeAgentRunResponse,
)
from services.benchmark_execution_adapter import BenchmarkExecutionAdapter
import services.benchmark_execution_adapter as adapter_module


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


def test_run_sync_delegates_to_sdk_public_api(monkeypatch) -> None:
    adapter = BenchmarkExecutionAdapter()
    sentinel_model = object()
    sentinel_vector_store = _CompatibleVectorStore()
    captured: dict[str, object] = {}

    def fake_run(query, *, vector_store, model, config=None):
        captured["query"] = query
        captured["vector_store"] = vector_store
        captured["model"] = model
        captured["config"] = config
        return RuntimeAgentRunResponse(main_question=query, output="sync output")

    monkeypatch.setattr(adapter_module.sdk_public_api, "run", fake_run)

    response = adapter.run_sync(
        "section 28 sync",
        vector_store=sentinel_vector_store,
        model=sentinel_model,
        config={"pipeline": {"decompose_enabled": False}},
    )

    assert isinstance(response, RuntimeAgentRunResponse)
    assert response.output == "sync output"
    assert captured == {
        "query": "section 28 sync",
        "vector_store": sentinel_vector_store,
        "model": sentinel_model,
        "config": {"pipeline": {"decompose_enabled": False}},
    }


def test_run_async_delegates_to_sdk_public_api(monkeypatch) -> None:
    adapter = BenchmarkExecutionAdapter()

    def fake_run_async(query, *, vector_store, model, config=None):
        assert query == "section 28 async"
        assert isinstance(vector_store, _CompatibleVectorStore)
        assert model is not None
        assert config == {"rerank": {"enabled": False}}
        return RuntimeAgentRunAsyncStartResponse(job_id="job-1", run_id="run-1", status="running")

    monkeypatch.setattr(adapter_module.sdk_public_api, "run_async", fake_run_async)

    response = adapter.run_async(
        "section 28 async",
        vector_store=_CompatibleVectorStore(),
        model=object(),
        config={"rerank": {"enabled": False}},
    )

    assert isinstance(response, RuntimeAgentRunAsyncStartResponse)
    assert response.model_dump() == {"job_id": "job-1", "run_id": "run-1", "status": "running"}


def test_get_run_status_delegates_to_sdk_public_api(monkeypatch) -> None:
    adapter = BenchmarkExecutionAdapter()

    def fake_get_run_status(job_id: str):
        assert job_id == "job-2"
        return RuntimeAgentRunAsyncStatusResponse(job_id=job_id, run_id="run-2", status="completed", stage="completed")

    monkeypatch.setattr(adapter_module.sdk_public_api, "get_run_status", fake_get_run_status)

    response = adapter.get_run_status("job-2")

    assert isinstance(response, RuntimeAgentRunAsyncStatusResponse)
    assert response.job_id == "job-2"
    assert response.status == "completed"


def test_cancel_run_delegates_to_sdk_public_api(monkeypatch) -> None:
    adapter = BenchmarkExecutionAdapter()

    def fake_cancel_run(job_id: str):
        assert job_id == "job-3"
        return RuntimeAgentRunAsyncCancelResponse(status="success", message="Cancellation requested.")

    monkeypatch.setattr(adapter_module.sdk_public_api, "cancel_run", fake_cancel_run)

    response = adapter.cancel_run("job-3")

    assert isinstance(response, RuntimeAgentRunAsyncCancelResponse)
    assert response.model_dump() == {"status": "success", "message": "Cancellation requested."}
