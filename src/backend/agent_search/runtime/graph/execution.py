from __future__ import annotations

from typing import Any, Mapping

from agent_search.runtime.graph.builder import build_runtime_graph
from agent_search.runtime.graph.state import RuntimeGraphContext, to_runtime_graph_state


def execute_runtime_graph(
    *,
    context: RuntimeGraphContext,
    run_metadata: Any,
    config: Mapping[str, Any] | None = None,
) -> Any:
    graph = build_runtime_graph()
    graph_input = to_runtime_graph_state(
        context.payload,
        run_metadata=run_metadata,
        initial_search_context=context.initial_search_context,
    )
    return graph.invoke(graph_input, config=config)


__all__ = ["execute_runtime_graph"]
