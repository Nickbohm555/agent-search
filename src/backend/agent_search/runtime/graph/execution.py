from __future__ import annotations

from collections.abc import Callable
from typing import Any, Mapping

from agent_search.runtime.graph.builder import build_runtime_graph
from agent_search.runtime.graph.state import RuntimeGraphContext, to_runtime_graph_state
from agent_search.runtime.lifecycle_events import LifecycleEventBuilder, RuntimeLifecycleEvent


def _iter_graph_stream(
    *,
    graph: Any,
    graph_input: Any,
    config: Mapping[str, Any],
) -> tuple[Any, list[tuple[str, Any]]]:
    terminal_state: Any = None
    signals: list[tuple[str, Any]] = []
    for item in graph.stream(
        graph_input,
        config=config,
        stream_mode=["values", "tasks", "updates", "checkpoints"],
    ):
        if isinstance(item, tuple) and len(item) == 2:
            mode, payload = item
        else:
            mode, payload = "values", item
        if mode == "values":
            terminal_state = payload
            continue
        signals.append((str(mode), payload))
    return terminal_state, signals


def _build_execution_config(
    *,
    run_metadata: Any,
    config: Mapping[str, Any] | None,
) -> dict[str, Any]:
    resolved = dict(config or {})
    configurable = dict(resolved.get("configurable") or {})
    configurable.setdefault("thread_id", getattr(run_metadata, "thread_id", ""))
    resolved["configurable"] = configurable
    return resolved


def execute_runtime_graph(
    *,
    context: RuntimeGraphContext,
    run_metadata: Any,
    config: Mapping[str, Any] | None = None,
    lifecycle_callback: Callable[[RuntimeLifecycleEvent], None] | None = None,
    resumed: bool = False,
) -> Any:
    graph = build_runtime_graph(context=context)
    graph_input = to_runtime_graph_state(
        context.payload,
        run_metadata=run_metadata,
        initial_search_context=context.initial_search_context,
    )
    execution_config = _build_execution_config(run_metadata=run_metadata, config=config)
    lifecycle_builder = LifecycleEventBuilder(run_metadata=run_metadata) if lifecycle_callback is not None else None
    try:
        if lifecycle_builder is not None:
            start_event = (
                lifecycle_builder.emit_recovery_started()
                if resumed
                else lifecycle_builder.emit_run_started()
            )
            lifecycle_callback(start_event)
        terminal_state, signals = _iter_graph_stream(graph=graph, graph_input=graph_input, config=execution_config)
        if lifecycle_builder is not None:
            for mode, payload in signals:
                for event in lifecycle_builder.consume_stream_signal(mode, payload):
                    lifecycle_callback(event)
            lifecycle_callback(lifecycle_builder.emit_terminal(status="success"))
        if terminal_state is None:
            return graph.invoke(graph_input, config=execution_config)
        return terminal_state
    except Exception as exc:
        if lifecycle_builder is not None:
            lifecycle_callback(lifecycle_builder.emit_terminal(status="error", error=str(exc)))
        raise


__all__ = ["execute_runtime_graph"]
