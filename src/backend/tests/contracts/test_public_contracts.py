from __future__ import annotations

import inspect
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from schemas import (
    BenchmarkMode,
    BenchmarkRunCreateRequest,
    BenchmarkRunStatusResponse,
    RuntimeAgentRunAsyncCancelResponse,
    RuntimeAgentRunAsyncStartResponse,
    RuntimeAgentRunAsyncStatusResponse,
    RuntimeAgentRunResponse,
)


def test_public_api_sync_signature_is_frozen() -> None:
    signature = inspect.signature(public_api.run)
    assert str(signature) == "(query: 'str', *, vector_store: 'Any', model: 'Any', config: 'dict[str, Any] | None' = None) -> 'RuntimeAgentRunResponse'"
    assert signature.parameters["query"].default is inspect._empty
    assert signature.parameters["vector_store"].default is inspect._empty
    assert signature.parameters["model"].default is inspect._empty


def test_public_api_async_signatures_are_frozen() -> None:
    run_async_signature = inspect.signature(public_api.run_async)
    assert str(run_async_signature) == "(query: 'str', *, vector_store: 'Any', model: 'Any', config: 'dict[str, Any] | None' = None) -> 'RuntimeAgentRunAsyncStartResponse'"

    status_signature = inspect.signature(public_api.get_run_status)
    assert str(status_signature) == "(job_id: 'str') -> 'RuntimeAgentRunAsyncStatusResponse'"

    cancel_signature = inspect.signature(public_api.cancel_run)
    assert str(cancel_signature) == "(job_id: 'str') -> 'RuntimeAgentRunAsyncCancelResponse'"


def test_public_api_return_annotations_are_runtime_models() -> None:
    annotations = inspect.get_annotations(public_api.run, eval_str=True)
    assert annotations["return"] is RuntimeAgentRunResponse

    annotations = inspect.get_annotations(public_api.run_async, eval_str=True)
    assert annotations["return"] is RuntimeAgentRunAsyncStartResponse

    annotations = inspect.get_annotations(public_api.get_run_status, eval_str=True)
    assert annotations["return"] is RuntimeAgentRunAsyncStatusResponse

    annotations = inspect.get_annotations(public_api.cancel_run, eval_str=True)
    assert annotations["return"] is RuntimeAgentRunAsyncCancelResponse


def test_benchmark_mode_enum_values_are_frozen() -> None:
    assert [mode.value for mode in BenchmarkMode] == ["baseline", "retrieval_only", "full"]


def test_benchmark_create_request_schema_is_frozen() -> None:
    schema = BenchmarkRunCreateRequest.model_json_schema()
    assert set(schema["properties"]) == {"dataset_id", "modes", "targets", "metadata"}
    assert schema["required"] == ["dataset_id", "modes"]
    assert schema["properties"]["dataset_id"]["minLength"] == 1
    assert schema["properties"]["modes"]["minItems"] == 1


def test_benchmark_run_status_response_schema_is_frozen() -> None:
    schema = BenchmarkRunStatusResponse.model_json_schema()
    assert set(schema["properties"]) == {
        "run_id",
        "status",
        "dataset_id",
        "modes",
        "targets",
        "mode_summaries",
        "completed_questions",
        "total_questions",
        "created_at",
        "started_at",
        "finished_at",
        "error",
    }
    assert schema["required"] == ["run_id", "status", "dataset_id"]
