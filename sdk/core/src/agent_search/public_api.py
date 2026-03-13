from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeoutError
import logging
from typing import Any, Mapping

from agent_search.config import RuntimeConfig
from agent_search.errors import (
    SDKConfigurationError,
    SDKError,
    SDKModelError,
    SDKRetrievalError,
    SDKTimeoutError,
)
from agent_search.runtime.runner import run_runtime_agent
from agent_search.vectorstore.protocol import assert_vector_store_compatible
from pydantic import ValidationError
from schemas import RuntimeAgentRunRequest, RuntimeAgentRunResponse

logger = logging.getLogger(__name__)


def _resolve_request_thread_id(config: Mapping[str, Any] | None = None) -> str | None:
    if not isinstance(config, Mapping):
        return None
    thread_id = config.get("thread_id")
    if thread_id is None:
        return None
    return str(thread_id)


def _map_sdk_error(*, operation: str, exc: Exception) -> SDKError:
    if isinstance(exc, SDKError):
        return exc
    if isinstance(exc, ValidationError):
        return SDKConfigurationError(f"{operation} failed due to invalid SDK input or configuration.")
    if isinstance(exc, (TimeoutError, FuturesTimeoutError)):
        return SDKTimeoutError(f"{operation} timed out.")

    message = str(exc).lower()
    if any(token in message for token in ("vector", "retriev", "document search", "similarity search")):
        return SDKRetrievalError(f"{operation} failed during retrieval.")
    if any(token in message for token in ("model", "llm", "openai", "completion", "chat")):
        return SDKModelError(f"{operation} failed during model execution.")
    if any(token in message for token in ("config", "invalid", "missing", "required", "argument")):
        return SDKConfigurationError(f"{operation} failed due to invalid SDK input or configuration.")

    return SDKError(f"{operation} failed.")


def advanced_rag(
    query: str,
    *,
    vector_store: Any,
    model: Any,
    config: dict[str, Any] | None = None,
    callbacks: list[Any] | None = None,
    langfuse_callback: Any | None = None,
    langfuse_settings: Mapping[str, Any] | None = None,
) -> RuntimeAgentRunResponse:
    logger.info(
        "SDK advanced_rag requested query_len=%s vector_store_type=%s model_type=%s has_config=%s has_callbacks=%s has_langfuse_callback=%s has_langfuse_settings=%s",
        len(query),
        type(vector_store).__name__,
        type(model).__name__,
        config is not None,
        bool(callbacks),
        langfuse_callback is not None,
        langfuse_settings is not None,
    )
    runtime_config = RuntimeConfig.from_dict(config)
    logger.info(
        "SDK sync runtime config resolved initial_k=%s rerank_enabled=%s rerank_provider=%s",
        runtime_config.retrieval.initial_search_context_k,
        runtime_config.rerank.enabled,
        runtime_config.rerank.provider,
    )
    if model is None:
        logger.error("SDK sync run rejected missing model")
        raise SDKConfigurationError("model is required and cannot be None")
    if vector_store is None:
        logger.error("SDK sync run rejected missing vector_store")
        raise SDKConfigurationError("vector_store is required and cannot be None")
    compatible_vector_store = assert_vector_store_compatible(vector_store)
    logger.info(
        "SDK sync run vector_store validated vector_store_type=%s",
        type(compatible_vector_store).__name__,
    )
    if langfuse_settings is not None and langfuse_callback is None:
        logger.warning(
            "SDK advanced_rag received langfuse_settings without langfuse_callback; "
            "settings are ignored and tracing remains disabled"
        )

    try:
        resolved_callbacks = list(callbacks or [])
        if langfuse_callback is not None:
            resolved_callbacks.append(langfuse_callback)
        response = run_runtime_agent(
            RuntimeAgentRunRequest(query=query, thread_id=_resolve_request_thread_id(config)),
            model=model,
            vector_store=compatible_vector_store,
            callbacks=resolved_callbacks or None,
            langfuse_callback=langfuse_callback,
        )
    except Exception as exc:  # noqa: BLE001
        mapped = _map_sdk_error(operation="advanced_rag", exc=exc)
        logger.exception(
            "SDK advanced_rag failed mapped_error=%s original_error=%s",
            type(mapped).__name__,
            type(exc).__name__,
        )
        raise mapped from exc
    logger.info(
        "SDK advanced_rag completed sub_qa_count=%s output_len=%s",
        len(response.sub_qa),
        len(response.output),
    )
    return response

