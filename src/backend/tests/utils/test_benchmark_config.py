from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from config import (
    BenchmarkRuntimeSettings,
    build_benchmark_execution_context,
    compute_benchmark_context_fingerprint,
    get_benchmark_context_fingerprint,
)


def test_benchmark_runtime_settings_defaults() -> None:
    settings = BenchmarkRuntimeSettings.from_env({})

    assert settings.default_dataset_id == "internal_v1"
    assert settings.judge_model == "gpt-4.1-mini"
    assert settings.run_timeout_cap_s == 1800
    assert settings.question_timeout_cap_s == 120
    assert settings.target_min_correctness == 0.75
    assert settings.target_p95_latency_ms == 30000
    assert settings.target_max_cost_usd == 5.0


def test_benchmark_runtime_settings_reads_env_overrides() -> None:
    settings = BenchmarkRuntimeSettings.from_env(
        {
            "BENCHMARK_DEFAULT_DATASET_ID": "internal_v2",
            "BENCHMARK_JUDGE_MODEL": "gpt-5-mini",
            "BENCHMARK_RUN_TIMEOUT_CAP_S": "2400",
            "BENCHMARK_QUESTION_TIMEOUT_CAP_S": "180",
            "BENCHMARK_TARGET_MIN_CORRECTNESS": "0.82",
            "BENCHMARK_TARGET_P95_LATENCY_MS": "25000",
            "BENCHMARK_TARGET_MAX_COST_USD": "7.5",
        }
    )

    assert settings.default_dataset_id == "internal_v2"
    assert settings.judge_model == "gpt-5-mini"
    assert settings.run_timeout_cap_s == 2400
    assert settings.question_timeout_cap_s == 180
    assert settings.target_min_correctness == 0.82
    assert settings.target_p95_latency_ms == 25000
    assert settings.target_max_cost_usd == 7.5


def test_benchmark_runtime_settings_falls_back_for_invalid_values() -> None:
    settings = BenchmarkRuntimeSettings.from_env(
        {
            "BENCHMARK_DEFAULT_DATASET_ID": "",
            "BENCHMARK_RUN_TIMEOUT_CAP_S": "0",
            "BENCHMARK_QUESTION_TIMEOUT_CAP_S": "abc",
            "BENCHMARK_TARGET_MIN_CORRECTNESS": "1.2",
            "BENCHMARK_TARGET_P95_LATENCY_MS": "-1",
            "BENCHMARK_TARGET_MAX_COST_USD": "-0.1",
        }
    )

    assert settings.default_dataset_id == "internal_v1"
    assert settings.run_timeout_cap_s == 1800
    assert settings.question_timeout_cap_s == 120
    assert settings.target_min_correctness == 0.75
    assert settings.target_p95_latency_ms == 30000
    assert settings.target_max_cost_usd == 5.0


def test_execution_context_fingerprint_is_stable_for_equivalent_context() -> None:
    settings = BenchmarkRuntimeSettings.from_env({})
    fingerprint_a = get_benchmark_context_fingerprint(
        settings,
        runtime_model="gpt-4.1-mini",
        extra={"provider": "openai", "region": "us"},
    )
    fingerprint_b = compute_benchmark_context_fingerprint(
        build_benchmark_execution_context(
            settings,
            runtime_model="gpt-4.1-mini",
            extra={"region": "us", "provider": "openai"},
        )
    )

    assert fingerprint_a == fingerprint_b
    assert len(fingerprint_a) == 64


def test_execution_context_fingerprint_changes_with_settings() -> None:
    default_settings = BenchmarkRuntimeSettings.from_env({})
    tuned_settings = BenchmarkRuntimeSettings.from_env({"BENCHMARK_TARGET_MIN_CORRECTNESS": "0.80"})

    default_fingerprint = get_benchmark_context_fingerprint(default_settings, runtime_model="gpt-4.1-mini")
    tuned_fingerprint = get_benchmark_context_fingerprint(tuned_settings, runtime_model="gpt-4.1-mini")

    assert default_fingerprint != tuned_fingerprint
