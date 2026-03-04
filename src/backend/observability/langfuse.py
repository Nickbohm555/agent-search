from dataclasses import dataclass
from contextlib import nullcontext
import os
from typing import Any, Optional

try:
    from langfuse import Langfuse as LangfuseClient
except ImportError:  # pragma: no cover - exercised when dependency is absent
    LangfuseClient = None


@dataclass
class LangfuseConfig:
    enabled: bool = False
    public_key: str = ""
    secret_key: str = ""
    host: str = "https://cloud.langfuse.com"
    environment: str = "development"
    release: str = "0.1.0"


@dataclass
class LangfuseTracingHandle:
    """Runtime tracing handle with graceful no-op behavior."""

    client: Optional[Any]
    tracer: Optional[Any]
    enabled: bool

    def start_as_current_span(self, name: str, **kwargs: Any) -> Any:
        """Create a Langfuse span context manager or return a no-op context."""
        if self.enabled and self.client is not None:
            return self.client.start_as_current_span(name=name, **kwargs)
        return nullcontext(_NoOpSpan())


class _NoOpSpan:
    """No-op span to keep tracing calls safe when disabled."""

    def update(self, **_: Any) -> None:
        return None


def load_langfuse_config() -> LangfuseConfig:
    enabled_raw = os.getenv("LANGFUSE_ENABLED", "false").strip().lower()
    enabled = enabled_raw in {"1", "true", "yes", "on"}
    return LangfuseConfig(
        enabled=enabled,
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        environment=os.getenv("LANGFUSE_ENVIRONMENT", "development"),
        release=os.getenv("LANGFUSE_RELEASE", "0.1.0"),
    )


def initialize_langfuse_tracing() -> LangfuseTracingHandle:
    """Initialize Langfuse client when enabled and correctly configured."""
    config = load_langfuse_config()
    if not config.enabled:
        return LangfuseTracingHandle(client=None, tracer=None, enabled=False)

    if not config.public_key or not config.secret_key:
        return LangfuseTracingHandle(client=None, tracer=None, enabled=False)

    if LangfuseClient is None:
        return LangfuseTracingHandle(client=None, tracer=None, enabled=False)

    try:
        client = LangfuseClient(
            public_key=config.public_key,
            secret_key=config.secret_key,
            host=config.host,
            environment=config.environment,
            release=config.release,
            tracing_enabled=True,
        )
    except Exception:
        return LangfuseTracingHandle(client=None, tracer=None, enabled=False)

    return LangfuseTracingHandle(client=client, tracer=client, enabled=True)
