from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
from typing import Any, Callable, Mapping

from agent_search.errors import SDKConfigurationError
from agent_search.runtime.graph.builder import build_runtime_graph
from agent_search.runtime.graph.execution import execute_runtime_graph
from agent_search.runtime.graph.state import RuntimeGraphContext, to_runtime_graph_state
from agent_search.runtime.lifecycle_events import LifecycleEventBuilder, RuntimeLifecycleEvent
from agent_search.runtime.persistence import compile_graph_with_checkpointer
from agent_search.runtime.resume import build_resume_command
from agent_search.runtime.state import to_rag_state
from langgraph.types import Command
from schemas import AgentGraphState, RuntimeAgentRunRequest, RuntimeAgentRunResponse
from services import agent_service as legacy_service
from services.idempotency_service import execute_idempotent_effect

logger = logging.getLogger(__name__)
_LEGACY_RUNNER_NODE_NAME = "legacy_parallel_graph_runner"


def _terminal_stage_name(stage_snapshots: list[Any]) -> str:
    if not stage_snapshots:
        return "runtime"
    last_stage = getattr(stage_snapshots[-1], "stage", "")
    return str(last_stage or "runtime")


@dataclass
class DurableExecutionOutcome:
    status: str
    state: Any | None = None
    response: RuntimeAgentRunResponse | None = None
    interrupt_payload: Any | None = None
    checkpoint_id: str | None = None


class _LegacyCompiledGraph:
    def __init__(
        self,
        *,
        payload: RuntimeAgentRunRequest,
        vector_store: Any,
        model: Any,
        run_metadata: Any,
        callbacks: list[Any] | None,
        initial_search_context: list[dict[str, Any]],
        snapshot_callback: Any | None,
    ) -> None:
        self._payload = payload
        self._vector_store = vector_store
        self._model = model
        self._run_metadata = run_metadata
        self._callbacks = callbacks
        self._initial_search_context = initial_search_context
        self._snapshot_callback = snapshot_callback

    def invoke(self, graph_input: RuntimeAgentRunRequest | Command, *, config: Mapping[str, Any] | None = None) -> DurableExecutionOutcome:
        if isinstance(graph_input, Command):
            raise SDKConfigurationError("No paused checkpoint exists for this run.")
        thread_id = None
        if isinstance(config, Mapping):
            configurable = config.get("configurable")
            if isinstance(configurable, Mapping):
                raw_thread_id = configurable.get("thread_id")
                if raw_thread_id is not None:
                    thread_id = str(raw_thread_id)
        if not thread_id:
            state = legacy_service.run_parallel_graph_runner(
                payload=graph_input,
                vector_store=self._vector_store,
                model=self._model,
                run_metadata=self._run_metadata,
                initial_search_context=self._initial_search_context,
                callbacks=self._callbacks,
                snapshot_callback=self._snapshot_callback,
            )
            response = legacy_service.map_graph_state_to_runtime_response(state)
            return DurableExecutionOutcome(
                status="completed",
                state=state,
                response=response,
                checkpoint_id=thread_id,
            )
        request_payload = graph_input.model_dump(mode="json")
        recorded_effect = execute_idempotent_effect(
            run_id=self._run_metadata.run_id,
            thread_id=thread_id,
            node_name=_LEGACY_RUNNER_NODE_NAME,
            effect_key=_build_effect_key(request_payload),
            request_payload=request_payload,
            effect_fn=lambda: self._invoke_and_serialize(graph_input=graph_input, thread_id=thread_id),
        )
        return _deserialize_recorded_outcome(recorded_effect.response_payload, thread_id=thread_id)

    def _invoke_and_serialize(
        self,
        *,
        graph_input: RuntimeAgentRunRequest,
        thread_id: str,
    ) -> dict[str, Any]:
        state = legacy_service.run_parallel_graph_runner(
            payload=graph_input,
            vector_store=self._vector_store,
            model=self._model,
            run_metadata=self._run_metadata,
            initial_search_context=self._initial_search_context,
            callbacks=self._callbacks,
            snapshot_callback=self._snapshot_callback,
        )
        response = legacy_service.map_graph_state_to_runtime_response(state)
        return {
            "status": "completed",
            "state": state.model_dump(mode="json"),
            "response": response.model_dump(mode="json"),
            "checkpoint_id": thread_id,
        }


class _LegacyGraphBuilder:
    def __init__(self, compiled_graph: _LegacyCompiledGraph) -> None:
        self._compiled_graph = compiled_graph

    def compile(self, **_kwargs: Any) -> _LegacyCompiledGraph:
        return self._compiled_graph


class _CheckpointedRuntimeGraphBuilder:
    def __init__(self, *, context: RuntimeGraphContext) -> None:
        self._context = context

    def compile(self, **compile_kwargs: Any) -> Any:
        return build_runtime_graph(context=self._context, **compile_kwargs)


def _coerce_durable_outcome(result: Any, *, thread_id: str) -> DurableExecutionOutcome:
    if isinstance(result, DurableExecutionOutcome):
        return result
    if isinstance(result, RuntimeAgentRunResponse):
        return DurableExecutionOutcome(status="completed", response=result, checkpoint_id=thread_id)
    if isinstance(result, Mapping):
        interrupt_payload = result.get("interrupt_payload", result.get("__interrupt__"))
        status = str(result.get("status", "paused" if interrupt_payload is not None else "completed"))
        return DurableExecutionOutcome(
            status=status,
            state=result.get("state"),
            response=result.get("response"),
            interrupt_payload=interrupt_payload,
            checkpoint_id=result.get("checkpoint_id", thread_id),
        )
    return DurableExecutionOutcome(status="completed", state=result, checkpoint_id=thread_id)


def _build_effect_key(request_payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(dict(request_payload), sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"request:{digest}"


def _deserialize_recorded_outcome(recorded_outcome: Mapping[str, Any], *, thread_id: str) -> DurableExecutionOutcome:
    state_payload = recorded_outcome.get("state")
    response_payload = recorded_outcome.get("response")
    state = AgentGraphState.model_validate(state_payload) if isinstance(state_payload, Mapping) else state_payload
    response = (
        RuntimeAgentRunResponse.model_validate(response_payload)
        if isinstance(response_payload, Mapping)
        else response_payload
    )
    return DurableExecutionOutcome(
        status=str(recorded_outcome.get("status", "completed")),
        state=state,
        response=response,
        checkpoint_id=str(recorded_outcome.get("checkpoint_id", thread_id)),
    )


def _checkpointed_hitl_enabled(payload: RuntimeAgentRunRequest) -> bool:
    controls = payload.controls
    return bool(
        controls is not None
        and controls.hitl is not None
        and (
            (
                controls.hitl.subquestions is not None
                and controls.hitl.subquestions.enabled
            )
            or (
                controls.hitl.query_expansion is not None
                and controls.hitl.query_expansion.enabled
            )
        )
    )


def _extract_checkpoint_id(payload: Any) -> str | None:
    if not isinstance(payload, Mapping):
        return None
    config = payload.get("config")
    if not isinstance(config, Mapping):
        return None
    configurable = config.get("configurable")
    if not isinstance(configurable, Mapping):
        return None
    raw_checkpoint_id = configurable.get("checkpoint_id")
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


def _run_subquestion_checkpointed_graph(
    payload: RuntimeAgentRunRequest,
    *,
    model: Any,
    vector_store: Any,
    run_metadata: Any,
    callbacks: list[Any] | None = None,
    lifecycle_callback: Callable[[RuntimeLifecycleEvent], None] | None = None,
    initial_search_context: list[dict[str, Any]] | None = None,
    snapshot_callback: Any | None = None,
    resume: Any | None = None,
    emit_success_terminal_event: bool = True,
    emit_paused_terminal_event: bool = True,
) -> DurableExecutionOutcome:
    context = RuntimeGraphContext(
        payload=payload,
        model=model,
        vector_store=vector_store,
        callbacks=list(callbacks or []),
        initial_search_context=list(initial_search_context or []),
    )
    builder = _CheckpointedRuntimeGraphBuilder(context=context)
    config = {
        "configurable": {
            "thread_id": run_metadata.thread_id,
            "checkpoint_id": run_metadata.thread_id,
        }
    }
    graph_input: RuntimeAgentRunRequest | Command | dict[str, Any]
    if resume is None:
        graph_input = to_runtime_graph_state(
            payload,
            run_metadata=run_metadata,
            initial_search_context=list(initial_search_context or []),
        )
    else:
        graph_input = build_resume_command(resume)

    lifecycle_builder = LifecycleEventBuilder(run_metadata=run_metadata) if lifecycle_callback is not None else None
    last_snapshot_count = 0
    latest_checkpoint_id: str | None = None
    interrupt_payload: Any | None = None
    terminal_state: Any | None = None

    with compile_graph_with_checkpointer(builder, checkpoint_db_url=payload.checkpoint_db_url) as graph:
        try:
            if lifecycle_builder is not None:
                if resume is None:
                    lifecycle_callback(lifecycle_builder.emit_run_started())
                else:
                    lifecycle_callback(lifecycle_builder.emit_recovery_started(checkpoint_id=run_metadata.thread_id))
            for item in graph.stream(
                graph_input,
                config=config,
                stream_mode=["values", "tasks", "updates", "checkpoints"],
            ):
                if isinstance(item, tuple) and len(item) == 2:
                    mode, payload_item = item
                else:
                    mode, payload_item = "values", item
                latest_checkpoint_id = _extract_checkpoint_id(payload_item) or latest_checkpoint_id
                interrupt_payload = _extract_interrupt_payload(payload_item) or interrupt_payload
                if lifecycle_builder is not None:
                    for event in lifecycle_builder.consume_stream_signal(str(mode), payload_item):
                        lifecycle_callback(event)
                if mode != "values":
                    continue
                terminal_state = payload_item
                if snapshot_callback is None:
                    continue
                rag_state = to_rag_state(payload_item)
                snapshots = rag_state["stage_snapshots"]
                while last_snapshot_count < len(snapshots):
                    snapshot_callback(snapshots[last_snapshot_count], rag_state)
                    last_snapshot_count += 1
            if interrupt_payload is not None:
                if lifecycle_builder is not None and emit_paused_terminal_event:
                    lifecycle_callback(lifecycle_builder.emit_terminal(status="paused"))
                return DurableExecutionOutcome(
                    status="paused",
                    state=terminal_state,
                    interrupt_payload=interrupt_payload,
                    checkpoint_id=latest_checkpoint_id or run_metadata.thread_id,
                )
            if terminal_state is None:
                terminal_state = graph.invoke(graph_input, config=config)
            response = legacy_service.map_graph_state_to_runtime_response(terminal_state)
            if lifecycle_builder is not None and emit_success_terminal_event:
                lifecycle_callback(lifecycle_builder.emit_terminal(status="success"))
            return DurableExecutionOutcome(
                status="completed",
                state=terminal_state,
                response=response,
                checkpoint_id=latest_checkpoint_id or run_metadata.thread_id,
            )
        except Exception as exc:
            if lifecycle_builder is not None:
                lifecycle_callback(lifecycle_builder.emit_terminal(status="error", error=str(exc)))
            raise


def run_checkpointed_agent(
    payload: RuntimeAgentRunRequest,
    *,
    model: Any,
    vector_store: Any,
    run_metadata: Any,
    callbacks: list[Any] | None = None,
    lifecycle_callback: Callable[[RuntimeLifecycleEvent], None] | None = None,
    initial_search_context: list[dict[str, Any]] | None = None,
    snapshot_callback: Any | None = None,
    resume: Any | None = None,
    emit_success_terminal_event: bool = True,
    emit_paused_terminal_event: bool = True,
) -> DurableExecutionOutcome:
    if _checkpointed_hitl_enabled(payload):
        return _run_subquestion_checkpointed_graph(
            payload,
            model=model,
            vector_store=vector_store,
            run_metadata=run_metadata,
            callbacks=callbacks,
            lifecycle_callback=lifecycle_callback,
            initial_search_context=initial_search_context,
            snapshot_callback=snapshot_callback,
            resume=resume,
            emit_success_terminal_event=emit_success_terminal_event,
            emit_paused_terminal_event=emit_paused_terminal_event,
        )
    compiled_graph = _LegacyCompiledGraph(
        payload=payload,
        vector_store=vector_store,
        model=model,
        run_metadata=run_metadata,
        callbacks=callbacks,
        initial_search_context=list(initial_search_context or []),
        snapshot_callback=snapshot_callback,
    )
    builder = _LegacyGraphBuilder(compiled_graph)
    config = {
        "configurable": {
            "thread_id": run_metadata.thread_id,
            "checkpoint_id": run_metadata.thread_id,
        }
    }
    graph_input: RuntimeAgentRunRequest | Command = payload
    if resume is not None:
        graph_input = build_resume_command(resume)
    lifecycle_builder = LifecycleEventBuilder(run_metadata=run_metadata) if lifecycle_callback is not None else None
    with compile_graph_with_checkpointer(builder, checkpoint_db_url=payload.checkpoint_db_url) as graph:
        try:
            if lifecycle_builder is not None:
                lifecycle_callback(lifecycle_builder.emit_recovery_started())
            result = graph.invoke(graph_input, config=config)
            outcome = _coerce_durable_outcome(result, thread_id=run_metadata.thread_id)
            if lifecycle_builder is not None:
                terminal_status = "paused" if outcome.status == "paused" else "success"
                should_emit_terminal = (
                    (terminal_status == "success" and emit_success_terminal_event)
                    or (terminal_status == "paused" and emit_paused_terminal_event)
                )
                if should_emit_terminal:
                    lifecycle_callback(lifecycle_builder.emit_terminal(status=terminal_status))
            return outcome
        except Exception as exc:
            if lifecycle_builder is not None:
                lifecycle_callback(lifecycle_builder.emit_terminal(status="error", error=str(exc)))
            raise


def run_runtime_agent(
    payload: RuntimeAgentRunRequest,
    *,
    model: Any | None = None,
    vector_store: Any | None = None,
    callbacks: list[Any] | None = None,
    lifecycle_callback: Callable[[RuntimeLifecycleEvent], None] | None = None,
) -> RuntimeAgentRunResponse:
    if model is None:
        logger.error("Runtime core run rejected missing model")
        raise SDKConfigurationError("model is required and cannot be None")
    if vector_store is None:
        logger.error("Runtime core run rejected missing vector_store")
        raise SDKConfigurationError("vector_store is required and cannot be None")
    run_metadata = legacy_service.build_graph_run_metadata(thread_id=payload.thread_id)
    logger.info(
        "Runtime core run start query=%s query_length=%s provided_model=%s provided_vector_store=%s run_id=%s trace_id=%s correlation_id=%s",
        legacy_service._truncate_query(payload.query),
        len(payload.query),
        model is not None,
        vector_store is not None,
        run_metadata.run_id,
        run_metadata.trace_id,
        run_metadata.correlation_id,
    )
    selected_vector_store = vector_store
    logger.info(
        "Runtime core vector store selected source=provided run_id=%s",
        run_metadata.run_id,
    )
    initial_search_context: list[dict[str, Any]] = []
    logger.info(
        "Runtime core initial context retrieval disabled; proceeding with empty context run_id=%s",
        run_metadata.run_id,
    )

    try:
        config = {
            "configurable": {
                "thread_id": run_metadata.thread_id,
                "checkpoint_id": run_metadata.thread_id,
            }
        }
        state = execute_runtime_graph(
            context=RuntimeGraphContext(
                payload=payload,
                model=model,
                vector_store=selected_vector_store,
                callbacks=list(callbacks or []),
                initial_search_context=initial_search_context,
            ),
            run_metadata=run_metadata,
            config=config,
            lifecycle_callback=lifecycle_callback,
        )
    except Exception:
        raise
    rag_state = to_rag_state(state)
    response = legacy_service.map_graph_state_to_runtime_response(state)
    logger.info(
        "Runtime core run complete sub_qa_count=%s output_length=%s snapshot_count=%s run_id=%s",
        len(response.sub_qa),
        len(response.output),
        len(rag_state["stage_snapshots"]),
        run_metadata.run_id,
    )
    return response
