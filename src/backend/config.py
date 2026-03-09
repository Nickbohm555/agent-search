from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import asdict, dataclass
from typing import Any, Mapping

logger = logging.getLogger(__name__)


def _read_str(env: Mapping[str, str], key: str, default: str) -> str:
    value = env.get(key, "").strip()
    if not value:
        return default
    return value


def _read_positive_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        parsed = int(raw)
    except ValueError:
        logger.warning("Invalid benchmark integer config key=%s value=%r default=%s", key, raw, default)
        return default
    if parsed <= 0:
        logger.warning("Non-positive benchmark integer config key=%s value=%s default=%s", key, parsed, default)
        return default
    return parsed


def _read_float_range(env: Mapping[str, str], key: str, default: float, *, min_value: float, max_value: float) -> float:
    raw = env.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        parsed = float(raw)
    except ValueError:
        logger.warning("Invalid benchmark float config key=%s value=%r default=%s", key, raw, default)
        return default
    if parsed < min_value or parsed > max_value:
        logger.warning(
            "Out-of-range benchmark float config key=%s value=%s min=%s max=%s default=%s",
            key,
            parsed,
            min_value,
            max_value,
            default,
        )
        return default
    return parsed


@dataclass(frozen=True)
class BenchmarkRuntimeSettings:
    default_dataset_id: str = "internal_v1"
    judge_model: str = "gpt-4.1-mini"
    run_timeout_cap_s: int = 1800
    question_timeout_cap_s: int = 120
    target_min_correctness: float = 0.75
    target_p95_latency_ms: int = 30000
    target_max_cost_usd: float = 5.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> BenchmarkRuntimeSettings:
        env_map = env or os.environ
        settings = cls(
            default_dataset_id=_read_str(env_map, "BENCHMARK_DEFAULT_DATASET_ID", "internal_v1"),
            judge_model=_read_str(env_map, "BENCHMARK_JUDGE_MODEL", "gpt-4.1-mini"),
            run_timeout_cap_s=_read_positive_int(env_map, "BENCHMARK_RUN_TIMEOUT_CAP_S", 1800),
            question_timeout_cap_s=_read_positive_int(env_map, "BENCHMARK_QUESTION_TIMEOUT_CAP_S", 120),
            target_min_correctness=_read_float_range(
                env_map,
                "BENCHMARK_TARGET_MIN_CORRECTNESS",
                0.75,
                min_value=0.0,
                max_value=1.0,
            ),
            target_p95_latency_ms=_read_positive_int(env_map, "BENCHMARK_TARGET_P95_LATENCY_MS", 30000),
            target_max_cost_usd=_read_float_range(
                env_map,
                "BENCHMARK_TARGET_MAX_COST_USD",
                5.0,
                min_value=0.0,
                max_value=1_000_000.0,
            ),
        )
        logger.info(
            "Benchmark settings loaded dataset_id=%s judge_model=%s run_timeout_cap_s=%s question_timeout_cap_s=%s",
            settings.default_dataset_id,
            settings.judge_model,
            settings.run_timeout_cap_s,
            settings.question_timeout_cap_s,
        )
        return settings


def build_benchmark_execution_context(
    settings: BenchmarkRuntimeSettings,
    *,
    runtime_model: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
        "settings": asdict(settings),
        "runtime_model": (runtime_model or "").strip() or None,
    }
    if extra:
        context["extra"] = dict(extra)
    return context


def compute_benchmark_context_fingerprint(context: Mapping[str, Any]) -> str:
    payload = json.dumps(context, sort_keys=True, separators=(",", ":"), default=str)
    fingerprint = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    logger.info("Benchmark execution context fingerprint computed fingerprint=%s", fingerprint)
    return fingerprint


def get_benchmark_context_fingerprint(
    settings: BenchmarkRuntimeSettings,
    *,
    runtime_model: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> str:
    context = build_benchmark_execution_context(settings, runtime_model=runtime_model, extra=extra)
    return compute_benchmark_context_fingerprint(context)
