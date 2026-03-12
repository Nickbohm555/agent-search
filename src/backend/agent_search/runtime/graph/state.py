from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from agent_search.runtime.state import RAGState, to_rag_state
from schemas import RuntimeAgentRunRequest


@dataclass(slots=True)
class RuntimeGraphContext:
    payload: RuntimeAgentRunRequest
    model: Any | None = None
    vector_store: Any | None = None
    callbacks: list[Any] = field(default_factory=list)
    langfuse_callback: Any | None = None
    initial_search_context: list[dict[str, Any]] = field(default_factory=list)


def to_runtime_graph_state(
    payload: RuntimeAgentRunRequest,
    *,
    run_metadata: Any,
    initial_search_context: list[dict[str, Any]] | None = None,
) -> RAGState:
    return to_rag_state(
        {
            "main_question": payload.query,
            "decomposition_sub_questions": [],
            "sub_question_artifacts": [],
            "final_answer": "",
            "citation_rows_by_index": {},
            "run_metadata": run_metadata,
            "sub_qa": [],
            "output": "",
            "stage_snapshots": [],
            "initial_search_context": list(initial_search_context or []),
        }
    )


RuntimeGraphState = RAGState
RuntimeGraphStateMapping = Mapping[str, Any]


__all__ = [
    "RuntimeGraphContext",
    "RuntimeGraphState",
    "RuntimeGraphStateMapping",
    "to_runtime_graph_state",
]
