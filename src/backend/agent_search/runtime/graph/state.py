from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from typing_extensions import TypedDict

from agent_search.runtime.state import (
    CitationRowsByIndexChannel,
    DecompositionSubQuestionsChannel,
    StageSnapshotsChannel,
    SubQAChannel,
    SubQuestionArtifactsChannel,
    to_rag_state,
)
from schemas import GraphRunMetadata, RuntimeAgentRunRequest


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
    run_metadata: GraphRunMetadata,
    initial_search_context: list[dict[str, Any]] | None = None,
) -> "RuntimeGraphState":
    base_state = to_rag_state(
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
        }
    )
    return RuntimeGraphState(
        **base_state,
        initial_search_context=list(initial_search_context or []),
    )


class RuntimeGraphState(TypedDict):
    main_question: str
    decomposition_sub_questions: DecompositionSubQuestionsChannel
    sub_question_artifacts: SubQuestionArtifactsChannel
    final_answer: str
    citation_rows_by_index: CitationRowsByIndexChannel
    run_metadata: GraphRunMetadata
    sub_qa: SubQAChannel
    output: str
    stage_snapshots: StageSnapshotsChannel
    initial_search_context: list[dict[str, Any]]


RuntimeGraphStateMapping = Mapping[str, Any]


__all__ = [
    "RuntimeGraphContext",
    "RuntimeGraphState",
    "RuntimeGraphStateMapping",
    "to_runtime_graph_state",
]
