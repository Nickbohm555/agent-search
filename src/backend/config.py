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


def _read_bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw = env.get(key)
    if raw is None or not raw.strip():
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    logger.warning("Invalid boolean config key=%s value=%r default=%s", key, raw, default)
    return default


def benchmarks_enabled(env: Mapping[str, str] | None = None) -> bool:
    env_map = os.environ if env is None else env
    return _read_bool(env_map, "BENCHMARKS_ENABLED", False)


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
        env_map = os.environ if env is None else env
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


@dataclass(frozen=True)
class LangfuseSettings:
    enabled: bool = False
    host: str = "https://cloud.langfuse.com"
    public_key: str = ""
    secret_key: str = ""
    environment: str = "development"
    release: str = "0.1.0"
    runtime_sample_rate: float = 1.0
    benchmark_sample_rate: float = 1.0

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> LangfuseSettings:
        env_map = os.environ if env is None else env
        settings = cls(
            enabled=_read_bool(env_map, "LANGFUSE_ENABLED", False),
            host=_read_str(
                env_map,
                "LANGFUSE_BASE_URL",
                _read_str(env_map, "LANGFUSE_HOST", "https://cloud.langfuse.com"),
            ),
            public_key=(env_map.get("LANGFUSE_PUBLIC_KEY", "").strip()),
            secret_key=(env_map.get("LANGFUSE_SECRET_KEY", "").strip()),
            environment=_read_str(env_map, "LANGFUSE_ENVIRONMENT", "development"),
            release=_read_str(env_map, "LANGFUSE_RELEASE", "0.1.0"),
            runtime_sample_rate=_read_float_range(
                env_map,
                "LANGFUSE_RUNTIME_SAMPLE_RATE",
                1.0,
                min_value=0.0,
                max_value=1.0,
            ),
            benchmark_sample_rate=_read_float_range(
                env_map,
                "LANGFUSE_BENCHMARK_SAMPLE_RATE",
                1.0,
                min_value=0.0,
                max_value=1.0,
            ),
        )
        logger.info(
            "Langfuse settings loaded enabled=%s host=%s runtime_sample_rate=%s benchmark_sample_rate=%s environment=%s release=%s",
            settings.enabled,
            settings.host,
            settings.runtime_sample_rate,
            settings.benchmark_sample_rate,
            settings.environment,
            settings.release,
        )
        return settings

    def has_credentials(self) -> bool:
        return bool(self.public_key and self.secret_key)

    def sample_rate_for_scope(self, scope: str) -> float:
        normalized_scope = scope.strip().lower()
        if normalized_scope == "benchmark":
            return self.benchmark_sample_rate
        return self.runtime_sample_rate


def should_sample_rate(sample_rate: float, *, sampling_key: str | None = None) -> bool:
    if sample_rate <= 0.0:
        return False
    if sample_rate >= 1.0:
        return True
    if not sampling_key:
        return True
    digest = hashlib.sha256(sampling_key.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    return bucket <= sample_rate


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
