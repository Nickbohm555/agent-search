from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from agent_search.errors import (
    SDKConfigurationError,
    SDKError,
    SDKModelError,
    SDKRetrievalError,
    SDKTimeoutError,
)


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


def test_sdk_error_hierarchy_is_explicit() -> None:
    assert issubclass(SDKConfigurationError, SDKError)
    assert issubclass(SDKRetrievalError, SDKError)
    assert issubclass(SDKModelError, SDKError)
    assert issubclass(SDKTimeoutError, SDKError)


def test_run_maps_retrieval_errors(monkeypatch) -> None:
    def fake_run_runtime_agent(*_args, **_kwargs):
        raise RuntimeError("Vector store retrieval failed")

    monkeypatch.setattr(public_api, "run_runtime_agent", fake_run_runtime_agent)

    try:
        public_api.run("query", vector_store=_CompatibleVectorStore(), model=object())
    except SDKRetrievalError as exc:
        assert str(exc) == "run failed during retrieval."
    else:
        raise AssertionError("Expected SDKRetrievalError")


def test_run_maps_model_errors(monkeypatch) -> None:
    def fake_run_runtime_agent(*_args, **_kwargs):
        raise RuntimeError("OpenAI model unavailable")

    monkeypatch.setattr(public_api, "run_runtime_agent", fake_run_runtime_agent)

    try:
        public_api.run("query", vector_store=_CompatibleVectorStore(), model=object())
    except SDKModelError as exc:
        assert str(exc) == "run failed during model execution."
    else:
        raise AssertionError("Expected SDKModelError")


def test_run_maps_timeout_errors(monkeypatch) -> None:
    def fake_run_runtime_agent(*_args, **_kwargs):
        raise TimeoutError("operation timed out")

    monkeypatch.setattr(public_api, "run_runtime_agent", fake_run_runtime_agent)

    try:
        public_api.run("query", vector_store=_CompatibleVectorStore(), model=object())
    except SDKTimeoutError as exc:
        assert str(exc) == "run timed out."
    else:
        raise AssertionError("Expected SDKTimeoutError")


def test_run_async_maps_configuration_errors(monkeypatch) -> None:
    def fake_start_agent_run_job(*_args, **_kwargs):
        raise ValueError("invalid config provided")

    monkeypatch.setattr(public_api, "start_agent_run_job", fake_start_agent_run_job)

    try:
        public_api.run_async("query", vector_store=_CompatibleVectorStore(), model=object())
    except SDKConfigurationError as exc:
        assert str(exc) == "run_async failed due to invalid SDK input or configuration."
    else:
        raise AssertionError("Expected SDKConfigurationError")


def test_get_run_status_maps_unknown_errors_to_base_sdk_error(monkeypatch) -> None:
    def fake_get_agent_run_job(_job_id):
        raise RuntimeError("unexpected failure")

    monkeypatch.setattr(public_api, "get_agent_run_job", fake_get_agent_run_job)

    try:
        public_api.get_run_status("job-123")
    except SDKError as exc:
        assert type(exc) is SDKError
        assert str(exc) == "get_run_status failed."
    else:
        raise AssertionError("Expected SDKError")
