from __future__ import annotations

import sys
from pathlib import Path

from pydantic import ValidationError

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schemas.benchmark import BenchmarkMode, BenchmarkRunCreateRequest
from services.benchmark_modes import get_mode_definition, get_mode_runtime_overrides, get_registered_modes


def test_benchmark_mode_registry_is_deterministic() -> None:
    assert [mode.value for mode in get_registered_modes()] == [
        "baseline_retrieve_then_answer",
        "agentic_default",
        "agentic_no_rerank",
        "agentic_single_query_no_decompose",
    ]


def test_benchmark_mode_registry_returns_expected_overrides() -> None:
    baseline = get_mode_definition(BenchmarkMode.baseline_retrieve_then_answer)
    assert baseline.runtime_config_overrides == {
        "rerank": {"enabled": False},
        "pipeline": {"decompose_enabled": False, "query_expansion_enabled": False},
    }

    no_rerank = get_mode_definition(BenchmarkMode.agentic_no_rerank)
    assert no_rerank.runtime_config_overrides == {"rerank": {"enabled": False}}

    single_query = get_mode_definition(BenchmarkMode.agentic_single_query_no_decompose)
    assert single_query.runtime_config_overrides == {
        "pipeline": {"decompose_enabled": False, "query_expansion_enabled": False},
    }


def test_mode_runtime_overrides_returns_copy() -> None:
    first = get_mode_runtime_overrides(BenchmarkMode.agentic_no_rerank)
    first["rerank"]["enabled"] = True

    second = get_mode_runtime_overrides(BenchmarkMode.agentic_no_rerank)
    assert second == {"rerank": {"enabled": False}}


def test_benchmark_schema_rejects_unknown_modes_at_validation_time() -> None:
    try:
        BenchmarkRunCreateRequest(
            dataset_id="internal_v1",
            modes=["agentic_default", "does_not_exist"],
        )
    except ValidationError as exc:
        assert "Unsupported benchmark modes: does_not_exist" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for unsupported benchmark mode")

