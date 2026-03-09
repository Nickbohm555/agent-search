from __future__ import annotations

import inspect
import logging
import threading
import uuid
from typing import Any, Literal

from config import LangfuseSettings, should_sample_rate

logger = logging.getLogger(__name__)

_LangfuseScope = Literal["runtime", "benchmark"]
_UNSET: object = object()
_cached_langfuse_client: Any | object = _UNSET
_cache_lock = threading.Lock()


def _normalize_identifier(value: str | None) -> str:
    if not value:
        return ""
    return value.strip()


def build_langfuse_run_metadata(
    *,
    run_id: str | None = None,
    thread_id: str | None = None,
    trace_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, str]:
    normalized_run_id = _normalize_identifier(run_id) or str(uuid.uuid4())
    normalized_thread_id = _normalize_identifier(thread_id) or normalized_run_id
    normalized_trace_id = _normalize_identifier(trace_id) or normalized_run_id
    normalized_correlation_id = _normalize_identifier(correlation_id) or normalized_run_id
    metadata = {
        "run_id": normalized_run_id,
        "thread_id": normalized_thread_id,
        "trace_id": normalized_trace_id,
        "correlation_id": normalized_correlation_id,
    }
    logger.info(
        "Langfuse run metadata prepared run_id=%s thread_id=%s trace_id=%s correlation_id=%s",
        metadata["run_id"],
        metadata["thread_id"],
        metadata["trace_id"],
        metadata["correlation_id"],
    )
    return metadata


def _load_callback_handler_class() -> Any | None:
    try:
        from langfuse.langchain import CallbackHandler

        return CallbackHandler
    except Exception:  # pragma: no cover - import path can vary by SDK version.
        try:
            from langfuse.callback import CallbackHandler  # type: ignore[attr-defined]

            return CallbackHandler
        except Exception:
            logger.exception("Langfuse tracing enabled but callback handler import failed")
            return None


def _build_langfuse_client(settings: LangfuseSettings) -> Any | None:
    if not settings.enabled:
        logger.info("Langfuse client bootstrap skipped: disabled")
        return None

    if not settings.has_credentials():
        logger.warning(
            "Langfuse client bootstrap skipped: missing credentials public_key_set=%s secret_key_set=%s",
            bool(settings.public_key),
            bool(settings.secret_key),
        )
        return None

    try:
        from langfuse import Langfuse
    except Exception:
        logger.exception("Langfuse tracing enabled but Langfuse module import failed")
        return None

    client_kwargs: dict[str, Any] = {
        "public_key": settings.public_key,
        "secret_key": settings.secret_key,
        "tracing_enabled": True,
        "host": settings.host,
        "environment": settings.environment,
        "release": settings.release,
    }
    signature = inspect.signature(Langfuse.__init__)
    accepted = set(signature.parameters.keys()) - {"self"}
    if "sample_rate" in accepted:
        client_kwargs["sample_rate"] = settings.runtime_sample_rate

    try:
        client = Langfuse(**client_kwargs)
    except Exception:
        logger.exception("Langfuse tracing enabled but Langfuse client init failed")
        return None

    logger.info(
        "Langfuse client initialized host=%s environment=%s release=%s runtime_sample_rate=%s",
        settings.host,
        settings.environment,
        settings.release,
        settings.runtime_sample_rate,
    )
    return client


def get_langfuse_client(*, settings: LangfuseSettings | None = None, force_reinit: bool = False) -> Any | None:
    global _cached_langfuse_client

    resolved_settings = settings or LangfuseSettings.from_env()
    with _cache_lock:
        if not force_reinit and _cached_langfuse_client is not _UNSET:
            return _cached_langfuse_client

        _cached_langfuse_client = _build_langfuse_client(resolved_settings)
        return _cached_langfuse_client


def _should_trace(settings: LangfuseSettings, *, scope: _LangfuseScope, sampling_key: str | None) -> bool:
    if not settings.enabled:
        logger.info("Langfuse tracing disabled enabled=%s", settings.enabled)
        return False

    scope_rate = settings.sample_rate_for_scope(scope)
    sampled = should_sample_rate(scope_rate, sampling_key=sampling_key)
    logger.info(
        "Langfuse trace sampling evaluated scope=%s sample_rate=%s sampled=%s sampling_key_provided=%s",
        scope,
        scope_rate,
        sampled,
        bool(sampling_key),
    )
    return sampled


def build_langfuse_callback_handler(
    *,
    scope: _LangfuseScope = "runtime",
    sampling_key: str | None = None,
    settings: LangfuseSettings | None = None,
) -> Any | None:
    """Create a Langfuse LangChain callback handler when tracing is enabled/sampled."""
    resolved_settings = settings or LangfuseSettings.from_env()
    if not _should_trace(resolved_settings, scope=scope, sampling_key=sampling_key):
        return None

    if not resolved_settings.has_credentials():
        logger.warning(
            "Langfuse tracing enabled but credentials are missing public_key_set=%s secret_key_set=%s",
            bool(resolved_settings.public_key),
            bool(resolved_settings.secret_key),
        )
        return None

    callback_handler_class = _load_callback_handler_class()
    if callback_handler_class is None:
        return None

    langfuse_client = get_langfuse_client(settings=resolved_settings)
    if langfuse_client is None:
        return None

    signature = inspect.signature(callback_handler_class.__init__)
    accepted = set(signature.parameters.keys()) - {"self"}
    kwargs: dict[str, Any] = {}
    if "public_key" in accepted:
        kwargs["public_key"] = resolved_settings.public_key
    if "secret_key" in accepted:
        kwargs["secret_key"] = resolved_settings.secret_key
    if "langfuse_public_key" in accepted:
        kwargs["langfuse_public_key"] = resolved_settings.public_key
    if "langfuse_secret_key" in accepted:
        kwargs["langfuse_secret_key"] = resolved_settings.secret_key
    if "host" in accepted:
        kwargs["host"] = resolved_settings.host
    elif "base_url" in accepted:
        kwargs["base_url"] = resolved_settings.host
    if "environment" in accepted:
        kwargs["environment"] = resolved_settings.environment
    if "release" in accepted:
        kwargs["release"] = resolved_settings.release

    try:
        handler = callback_handler_class(**kwargs)
    except Exception:
        logger.exception("Failed to initialize Langfuse callback handler")
        return None

    setattr(handler, "_agent_search_langfuse_client", langfuse_client)
    logger.info(
        "Langfuse callback handler initialized scope=%s host=%s environment=%s release=%s",
        scope,
        resolved_settings.host,
        resolved_settings.environment,
        resolved_settings.release,
    )
    return handler


def flush_langfuse_callback_handler(handler: Any | None) -> None:
    """Best-effort flush so traces are quickly available for external harness reads."""
    if handler is None:
        return
    try:
        flush = getattr(handler, "flush", None)
        if callable(flush):
            flush()
            logger.info("Langfuse callback flush completed via handler.flush()")
            return
        client = getattr(handler, "langfuse", None)
        client_flush = getattr(client, "flush", None)
        if callable(client_flush):
            client_flush()
            logger.info("Langfuse callback flush completed via handler.langfuse.flush()")
            return
        attached_client = getattr(handler, "_agent_search_langfuse_client", None)
        attached_client_flush = getattr(attached_client, "flush", None)
        if callable(attached_client_flush):
            attached_client_flush()
            logger.info("Langfuse callback flush completed via attached Langfuse client")
            return
        logger.info("Langfuse callback flush skipped; no flush method found")
    except Exception:
        logger.exception("Langfuse callback flush failed")
