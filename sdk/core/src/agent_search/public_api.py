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
from agent_search.runtime.graph.builder import build_runtime_graph
from agent_search.runtime.graph.state import RuntimeGraphContext, to_runtime_graph_state
from agent_search.runtime.persistence import compile_graph_with_checkpointer
from agent_search.runtime.resume import build_resume_command
from agent_search.runtime.runner import run_runtime_agent
from agent_search.vectorstore.protocol import assert_vector_store_compatible
from pydantic import ValidationError
from schemas import RuntimeAgentRunControls, RuntimeAgentRunRequest, RuntimeAgentRunResponse
from schemas.agent import RuntimeAgentRunResult
from services import agent_service as legacy_service

logger = logging.getLogger(__name__)
_CUSTOM_PROMPT_KEYS = ("subanswer", "synthesis")


def _resolve_request_thread_id(config: Mapping[str, Any] | None = None) -> str | None:
    if not isinstance(config, Mapping):
        return None
    thread_id = config.get("thread_id")
    if thread_id is None:
        return None
    return str(thread_id)


def _resolve_resume_checkpoint_id(resume: Any | None = None) -> str | None:
    checkpoint_id = getattr(resume, "checkpoint_id", None)
    if checkpoint_id is None and isinstance(resume, Mapping):
        checkpoint_id = resume.get("checkpoint_id")
    return str(checkpoint_id).strip() if checkpoint_id is not None else None


def _get_nested_mapping(config: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(config, Mapping):
        return None
    value = config.get(key)
    if isinstance(value, Mapping):
        return value
    return None


def _get_custom_prompt_mapping(config: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if not isinstance(config, Mapping):
        return None

    for key in ("custom_prompts", "custom-prompts"):
        value = config.get(key)
        if isinstance(value, Mapping):
            return dict(value)
    return None


def _build_effective_custom_prompts(config: Mapping[str, Any] | None) -> dict[str, Any] | None:
    prompt_defaults = _get_custom_prompt_mapping(config)
    runtime_config = _get_nested_mapping(config, "runtime_config")
    prompt_overrides = _get_custom_prompt_mapping(runtime_config)
    if prompt_defaults is None and prompt_overrides is None:
        return None

    merged_prompts: dict[str, Any] = {}
    if prompt_defaults is not None:
        merged_prompts.update(prompt_defaults)
    if prompt_overrides is not None:
        merged_prompts.update(prompt_overrides)
    return merged_prompts


def _resolve_runtime_config_input(config: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if not isinstance(config, Mapping):
        return None

    resolved: dict[str, Any] = dict(config)
    effective_custom_prompts = _build_effective_custom_prompts(config)
    if effective_custom_prompts is not None:
        resolved["custom_prompts"] = effective_custom_prompts
    return resolved


def _build_runtime_request_payload(
    query: str,
    *,
    config: Mapping[str, Any] | None,
    runtime_config: RuntimeConfig,
    resume: Any | None = None,
) -> RuntimeAgentRunRequest:
    custom_prompts_payload = {
        key: value
        for key in _CUSTOM_PROMPT_KEYS
        if (value := getattr(runtime_config.custom_prompts, key)) is not None
    }
    return RuntimeAgentRunRequest(
        query=query,
        thread_id=_resolve_request_thread_id(config) or _resolve_resume_checkpoint_id(resume),
        controls=(
            RuntimeAgentRunControls.model_validate(config.get("controls"))
            if isinstance(config, Mapping) and isinstance(config.get("controls"), Mapping)
            else None
        ),
        custom_prompts=(
            custom_prompts_payload
            if custom_prompts_payload
            else None
        ),
    )


def _hitl_requested(payload: RuntimeAgentRunRequest, *, resume: Any | None = None) -> bool:
    if resume is not None:
        return True
    return bool(payload.controls and payload.controls.hitl and payload.controls.hitl.enabled)


def _extract_checkpoint_id(payload: Any) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    raw_checkpoint_id = payload.get("checkpoint_id")
    if raw_checkpoint_id is not None:
        return str(raw_checkpoint_id)
    config = payload.get("config")
    if not isinstance(config, Mapping):
        return None
    configurable = config.get("configurable")
    if not isinstance(configurable, Mapping):
        return None
    raw_checkpoint_id = configurable.get("checkpoint_id") or configurable.get("thread_id")
    if raw_checkpoint_id is None:
        return None
    return str(raw_checkpoint_id)


def _extract_interrupt_payload(payload: Any) -> Any | None:
    if not isinstance(payload, Mapping):
        return None
    interrupts = payload.get("interrupts")
    if isinstance(interrupts, list) and interrupts:
        first_interrupt = interrupts[0]
        if isinstance(first_interrupt, Mapping):
            return first_interrupt.get("value")
    interrupt_update = payload.get("__interrupt__")
    if isinstance(interrupt_update, (list, tuple)) and interrupt_update:
        first_interrupt = interrupt_update[0]
        value = getattr(first_interrupt, "value", None)
        if value is not None:
            return value
    return None


class _RuntimeGraphBuilder:
    def __init__(self, *, context: RuntimeGraphContext) -> None:
        self._context = context

    def compile(self, **compile_kwargs: Any) -> Any:
        return build_runtime_graph(context=self._context, **compile_kwargs)


def _run_hitl_runtime_agent(
    payload: RuntimeAgentRunRequest,
    *,
    model: Any,
    vector_store: Any,
    callbacks: list[Any] | None = None,
    langfuse_callback: Any | None = None,
    resume: Any | None = None,
) -> RuntimeAgentRunResult:
    run_metadata = legacy_service.build_graph_run_metadata(thread_id=payload.thread_id)
    context = RuntimeGraphContext(
        payload=payload,
        model=model,
        vector_store=vector_store,
        callbacks=list(callbacks or []),
        langfuse_callback=langfuse_callback,
        initial_search_context=[],
    )
    builder = _RuntimeGraphBuilder(context=context)
    graph_input: Any = (
        to_runtime_graph_state(payload, run_metadata=run_metadata, initial_search_context=[])
        if resume is None
        else build_resume_command(resume)
    )
    execution_config = {"configurable": {"thread_id": run_metadata.thread_id}}
    terminal_state: Any = None
    latest_checkpoint_id: str | None = None
    interrupt_payload: Any | None = None
    with compile_graph_with_checkpointer(builder) as graph:
        for item in graph.stream(
            graph_input,
            config=execution_config,
            stream_mode=["values", "tasks", "updates", "checkpoints"],
        ):
            if isinstance(item, tuple) and len(item) == 2:
                mode, payload_item = item
            else:
                mode, payload_item = "values", item
            latest_checkpoint_id = _extract_checkpoint_id(payload_item) or latest_checkpoint_id
            interrupt_payload = _extract_interrupt_payload(payload_item) or interrupt_payload
            if mode == "values":
                terminal_state = payload_item
        if interrupt_payload is not None:
            return RuntimeAgentRunResult(
                status="paused",
                thread_id=run_metadata.thread_id,
                checkpoint_id=run_metadata.thread_id,
                interrupt_payload=interrupt_payload,
            )
        if terminal_state is None:
            terminal_state = graph.invoke(graph_input, config=execution_config)
    response = legacy_service.map_graph_state_to_runtime_response(terminal_state)
    return RuntimeAgentRunResult(
        status="completed",
        thread_id=run_metadata.thread_id,
        checkpoint_id=run_metadata.thread_id,
        response=response,
    )


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
    resume: Any | None = None,
) -> RuntimeAgentRunResponse | RuntimeAgentRunResult:
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
    runtime_config = RuntimeConfig.from_dict(_resolve_runtime_config_input(config))
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
        request_payload = _build_runtime_request_payload(query, config=config, runtime_config=runtime_config, resume=resume)
        if _hitl_requested(request_payload, resume=resume):
            response = _run_hitl_runtime_agent(
                request_payload,
                model=model,
                vector_store=compatible_vector_store,
                callbacks=resolved_callbacks or None,
                langfuse_callback=langfuse_callback,
                resume=resume,
            )
        else:
            response = run_runtime_agent(
                request_payload,
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
        "SDK advanced_rag completed status=%s sub_qa_count=%s output_len=%s",
        getattr(response, "status", "completed"),
        (
            len(response.response.sub_qa)
            if isinstance(response, RuntimeAgentRunResult) and response.response is not None
            else 0 if isinstance(response, RuntimeAgentRunResult)
            else len(response.sub_qa)
        ),
        (
            len(response.response.output)
            if isinstance(response, RuntimeAgentRunResult) and response.response is not None
            else 0 if isinstance(response, RuntimeAgentRunResult)
            else len(response.output)
        ),
    )
    return response
