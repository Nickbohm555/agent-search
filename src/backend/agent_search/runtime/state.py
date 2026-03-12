from __future__ import annotations

import operator
from typing import Annotated, Any, Mapping, cast
from typing_extensions import TypedDict

from schemas import (
    AgentGraphState,
    CitationSourceRow,
    GraphRunMetadata,
    GraphStageSnapshot,
    SubQuestionAnswer,
    SubQuestionArtifacts,
)

DecompositionSubQuestionsChannel = Annotated[list[str], operator.add]
SubQuestionArtifactsChannel = Annotated[list[SubQuestionArtifacts], operator.add]
CitationRowsByIndexChannel = Annotated[dict[int, CitationSourceRow], operator.or_]
SubQAChannel = Annotated[list[SubQuestionAnswer], operator.add]
StageSnapshotsChannel = Annotated[list[GraphStageSnapshot], operator.add]


class RAGState(TypedDict):
    main_question: str
    decomposition_sub_questions: DecompositionSubQuestionsChannel
    sub_question_artifacts: SubQuestionArtifactsChannel
    final_answer: str
    citation_rows_by_index: CitationRowsByIndexChannel
    run_metadata: GraphRunMetadata
    sub_qa: SubQAChannel
    output: str
    stage_snapshots: StageSnapshotsChannel


def _copy_rag_state(state: Mapping[str, Any]) -> RAGState:
    return RAGState(
        main_question=str(state["main_question"]),
        decomposition_sub_questions=list(state["decomposition_sub_questions"]),
        sub_question_artifacts=[
            artifact.model_copy(deep=True) for artifact in cast(list[SubQuestionArtifacts], state["sub_question_artifacts"])
        ],
        final_answer=str(state["final_answer"]),
        citation_rows_by_index={
            int(index): row.model_copy(deep=True)
            for index, row in cast(dict[int, CitationSourceRow], state["citation_rows_by_index"]).items()
        },
        run_metadata=cast(GraphRunMetadata, state["run_metadata"]).model_copy(deep=True),
        sub_qa=[item.model_copy(deep=True) for item in cast(list[SubQuestionAnswer], state["sub_qa"])],
        output=str(state["output"]),
        stage_snapshots=[
            snapshot.model_copy(deep=True) for snapshot in cast(list[GraphStageSnapshot], state["stage_snapshots"])
        ],
    )


def to_rag_state(state: AgentGraphState | Mapping[str, Any]) -> RAGState:
    if isinstance(state, AgentGraphState):
        return RAGState(
            main_question=state.main_question,
            decomposition_sub_questions=list(state.decomposition_sub_questions),
            sub_question_artifacts=[item.model_copy(deep=True) for item in state.sub_question_artifacts],
            final_answer=state.final_answer,
            citation_rows_by_index={
                index: row.model_copy(deep=True) for index, row in state.citation_rows_by_index.items()
            },
            run_metadata=state.run_metadata.model_copy(deep=True),
            sub_qa=[item.model_copy(deep=True) for item in state.sub_qa],
            output=state.output,
            stage_snapshots=[item.model_copy(deep=True) for item in state.stage_snapshots],
        )
    return _copy_rag_state(state)


def from_rag_state(state: AgentGraphState | Mapping[str, Any]) -> AgentGraphState:
    normalized = to_rag_state(state)
    return AgentGraphState(
        main_question=normalized["main_question"],
        decomposition_sub_questions=list(normalized["decomposition_sub_questions"]),
        sub_question_artifacts=[item.model_copy(deep=True) for item in normalized["sub_question_artifacts"]],
        final_answer=normalized["final_answer"],
        citation_rows_by_index={
            index: row.model_copy(deep=True) for index, row in normalized["citation_rows_by_index"].items()
        },
        run_metadata=normalized["run_metadata"].model_copy(deep=True),
        sub_qa=[item.model_copy(deep=True) for item in normalized["sub_qa"]],
        output=normalized["output"],
        stage_snapshots=[item.model_copy(deep=True) for item in normalized["stage_snapshots"]],
    )
