from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Mapping

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


def _read_float_range(env: Mapping[str, str], key: str, default: float, *, min_value: float, max_value: float) -> float:
    raw = env.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        parsed = float(raw)
    except ValueError:
        logger.warning("Invalid float config key=%s value=%r default=%s", key, raw, default)
        return default
    if parsed < min_value or parsed > max_value:
        logger.warning(
            "Out-of-range float config key=%s value=%s min=%s max=%s default=%s",
            key,
            parsed,
            min_value,
            max_value,
            default,
        )
        return default
    return parsed


@dataclass(frozen=True)
class LangfuseSettings:
    enabled: bool = False
    host: str = "https://cloud.langfuse.com"
    public_key: str = ""
    secret_key: str = ""
    environment: str = "development"
    release: str = "0.1.0"
    runtime_sample_rate: float = 1.0

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
        )
        logger.info(
            "Langfuse settings loaded enabled=%s host=%s runtime_sample_rate=%s environment=%s release=%s",
            settings.enabled,
            settings.host,
            settings.runtime_sample_rate,
            settings.environment,
            settings.release,
        )
        return settings

    def has_credentials(self) -> bool:
        return bool(self.public_key and self.secret_key)

    def sample_rate_for_scope(self, scope: str) -> float:
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
