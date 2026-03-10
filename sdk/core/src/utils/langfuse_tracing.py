from __future__ import annotations

import inspect
import logging
import threading
import uuid
from typing import Any, Iterable, Literal, Mapping

from config import LangfuseSettings, should_sample_rate

logger = logging.getLogger(__name__)

_LangfuseScope = Literal["runtime"]
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


def _as_dict(mapping: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(mapping) if isinstance(mapping, Mapping) else {}


def _call_with_supported_kwargs(target: Any, kwargs: Mapping[str, Any]) -> Any:
    signature = inspect.signature(target)
    accepts_kwargs = any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values())
    if accepts_kwargs:
        filtered_kwargs = {key: value for key, value in kwargs.items() if value is not None}
    else:
        accepted = set(signature.parameters.keys())
        filtered_kwargs = {key: value for key, value in kwargs.items() if key in accepted and value is not None}
    return target(**filtered_kwargs)


def _first_callable(target: Any, candidate_names: Iterable[str]) -> Any | None:
    for name in candidate_names:
        candidate = getattr(target, name, None)
        if callable(candidate):
            return candidate
    return None


def _resolve_observation_client(observation: Any) -> Any | None:
    if observation is None:
        return None
    for attr_name in ("langfuse", "client", "_agent_search_langfuse_client"):
        candidate = getattr(observation, attr_name, None)
        if candidate is not None:
            return candidate
    return None


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


def start_langfuse_trace(
    *,
    name: str,
    scope: _LangfuseScope,
    sampling_key: str,
    input_payload: Any | None = None,
    metadata: Mapping[str, Any] | None = None,
    trace_id: str | None = None,
    session_id: str | None = None,
    settings: LangfuseSettings | None = None,
) -> Any | None:
    resolved_settings = settings or LangfuseSettings.from_env()
    if not _should_trace(resolved_settings, scope=scope, sampling_key=sampling_key):
        return None

    langfuse_client = get_langfuse_client(settings=resolved_settings)
    if langfuse_client is None:
        return None

    kwargs: dict[str, Any] = {
        "name": name,
        "input": input_payload,
        "metadata": _as_dict(metadata) or None,
        "id": trace_id,
        "trace_id": trace_id,
        "session_id": session_id,
    }

    trace_builder = _first_callable(langfuse_client, ("trace", "create_trace", "start_trace"))
    if trace_builder is not None:
        try:
            trace = _call_with_supported_kwargs(trace_builder, kwargs)
            setattr(trace, "_agent_search_langfuse_client", langfuse_client)
            logger.info("Langfuse trace started name=%s scope=%s", name, scope)
            return trace
        except Exception:
            logger.exception("Langfuse trace start failed name=%s scope=%s", name, scope)
            return None

    # Langfuse v3 no longer exposes trace constructors on the client.
    # Fall back to a root span/observation with explicit trace context.
    observation_builder = _first_callable(langfuse_client, ("start_span", "start_observation"))
    if observation_builder is None:
        logger.warning("Langfuse trace start skipped; client has no trace/span constructor")
        return None

    observation_kwargs: dict[str, Any] = {
        "name": name,
        "input": input_payload,
        "metadata": _as_dict(metadata) or None,
    }
    trace_context = {k: v for k, v in {"trace_id": trace_id, "session_id": session_id}.items() if v}
    if trace_context:
        observation_kwargs["trace_context"] = trace_context
    try:
        root_observation = _call_with_supported_kwargs(observation_builder, observation_kwargs)
        setattr(root_observation, "_agent_search_langfuse_client", langfuse_client)
        logger.info("Langfuse trace started via span fallback name=%s scope=%s", name, scope)
        return root_observation
    except Exception:
        logger.exception("Langfuse trace/span fallback start failed name=%s scope=%s", name, scope)
        return None


def start_langfuse_span(
    *,
    parent: Any | None,
    name: str,
    input_payload: Any | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Any | None:
    if parent is None:
        return None

    span_builder = _first_callable(parent, ("span", "create_span", "start_span"))
    if span_builder is None:
        logger.info("Langfuse span start skipped name=%s reason=no_parent_span_builder", name)
        return None

    kwargs: dict[str, Any] = {
        "name": name,
        "input": input_payload,
        "metadata": _as_dict(metadata) or None,
    }
    try:
        span = _call_with_supported_kwargs(span_builder, kwargs)
        logger.info("Langfuse span started name=%s", name)
        return span
    except Exception:
        logger.exception("Langfuse span start failed name=%s", name)
        return None


def end_langfuse_observation(
    observation: Any | None,
    *,
    output_payload: Any | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    if observation is None:
        return
    update_call = _first_callable(observation, ("update", "set_output"))
    end_call = _first_callable(observation, ("end", "close", "finish"))
    payload = _as_dict(metadata)
    try:
        if update_call is not None:
            update_kwargs = {"output": output_payload, "metadata": payload or None}
            _call_with_supported_kwargs(update_call, update_kwargs)
        # Langfuse v3 span.end() can block while exporting. We already persist output
        # via update(), so avoid blocking end calls on those SDK internals.
        if end_call is not None and getattr(end_call, "__module__", "").startswith("langfuse._client"):
            logger.info("Langfuse observation end skipped for v3 client method=%s", getattr(end_call, "__qualname__", "end"))
            end_call = None
        if end_call is not None:
            end_kwargs = {"output": output_payload, "metadata": payload or None}
            _call_with_supported_kwargs(end_call, end_kwargs)
        logger.info("Langfuse observation closed has_update=%s has_end=%s", update_call is not None, end_call is not None)
    except Exception:
        logger.exception("Langfuse observation close failed")


def record_langfuse_score(
    *,
    parent: Any | None,
    name: str,
    value: float,
    comment: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    if parent is None:
        return
    score_call = _first_callable(parent, ("score", "create_score", "log_score"))
    if score_call is None:
        client = _resolve_observation_client(parent)
        score_call = _first_callable(client, ("score", "create_score", "log_score")) if client is not None else None
    if score_call is None:
        logger.info("Langfuse score skipped name=%s reason=no_score_api", name)
        return

    kwargs: dict[str, Any] = {
        "name": name,
        "value": float(value),
        "score": float(value),
        "comment": comment,
        "metadata": _as_dict(metadata) or None,
    }
    try:
        _call_with_supported_kwargs(score_call, kwargs)
        logger.info("Langfuse score recorded name=%s value=%s", name, value)
    except Exception:
        logger.exception("Langfuse score record failed name=%s", name)


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
