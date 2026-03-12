from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from agent_search.runtime.graph.state import RuntimeGraphState


def _bootstrap_runtime_state(state: RuntimeGraphState) -> RuntimeGraphState:
    return state


def build_runtime_graph(**compile_kwargs: Any) -> Any:
    builder = StateGraph(RuntimeGraphState)
    builder.add_node("bootstrap", _bootstrap_runtime_state)
    builder.add_edge(START, "bootstrap")
    builder.add_edge("bootstrap", END)
    return builder.compile(**compile_kwargs)


__all__ = ["build_runtime_graph"]
