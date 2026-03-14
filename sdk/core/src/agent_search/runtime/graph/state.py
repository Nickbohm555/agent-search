from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Any, Mapping

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


def _merge_stable_main_question(current: str, update: str) -> str:
    if current and update and current != update:
        raise ValueError(f"main_question must remain stable across graph lanes: {current!r} != {update!r}")
    return update or current


def _merge_stable_optional_text(current: str, update: str) -> str:
    if current and update and current != update:
        raise ValueError(f"text channel must remain stable across graph lanes: {current!r} != {update!r}")
    return update or current


def _merge_stable_run_metadata(current: GraphRunMetadata, update: GraphRunMetadata) -> GraphRunMetadata:
    if current.model_dump(mode="json") != update.model_dump(mode="json"):
        raise ValueError("run_metadata must remain stable across graph lanes.")
    return update.model_copy(deep=True)


def _merge_stable_initial_search_context(
    current: list[dict[str, Any]],
    update: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if current and update and current != update:
        raise ValueError("initial_search_context must remain stable across graph lanes.")
    return [dict(item) for item in (update or current)]


def _merge_stable_bool(current: bool, update: bool) -> bool:
    if current == update:
        return update
    return current or update


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
        subquestion_hitl_enabled=bool(
            payload.controls
            and payload.controls.hitl
            and payload.controls.hitl.subquestions
            and payload.controls.hitl.subquestions.enabled
        ),
        query_expansion_hitl_enabled=bool(
            payload.controls
            and payload.controls.hitl
            and payload.controls.hitl.query_expansion
            and payload.controls.hitl.query_expansion.enabled
        ),
    )


class RuntimeGraphState(TypedDict):
    main_question: Annotated[str, _merge_stable_main_question]
    decomposition_sub_questions: DecompositionSubQuestionsChannel
    sub_question_artifacts: SubQuestionArtifactsChannel
    final_answer: Annotated[str, _merge_stable_optional_text]
    citation_rows_by_index: CitationRowsByIndexChannel
    run_metadata: Annotated[GraphRunMetadata, _merge_stable_run_metadata]
    sub_qa: SubQAChannel
    output: Annotated[str, _merge_stable_optional_text]
    stage_snapshots: StageSnapshotsChannel
    initial_search_context: Annotated[list[dict[str, Any]], _merge_stable_initial_search_context]
    subquestion_hitl_enabled: Annotated[bool, _merge_stable_bool]
    query_expansion_hitl_enabled: Annotated[bool, _merge_stable_bool]


RuntimeGraphStateMapping = Mapping[str, Any]


__all__ = [
    "RuntimeGraphContext",
    "RuntimeGraphState",
    "RuntimeGraphStateMapping",
    "to_runtime_graph_state",
]
