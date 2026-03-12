from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RuntimeAgentRunRequest(BaseModel):
    query: str = Field(min_length=1)
    thread_id: str | None = None


class SubQuestionAnswer(BaseModel):
    sub_question: str
    sub_answer: str
    tool_call_input: str = ""
    expanded_query: str = ""
    sub_agent_response: str = ""
    answerable: bool = False
    verification_reason: str = ""


class RuntimeAgentRunResponse(BaseModel):
    main_question: str = ""
    thread_id: str = ""
    sub_qa: list[SubQuestionAnswer] = Field(default_factory=list)
    output: str
    final_citations: list["CitationSourceRow"] = Field(default_factory=list)


class AgentRunStageMetadata(BaseModel):
    stage: str
    status: str
    sub_question: str = ""
    lane_index: int = 0
    lane_total: int = 0
    emitted_at: float | None = None


class RuntimeAgentRunAsyncStartResponse(BaseModel):
    job_id: str
    run_id: str
    thread_id: str = ""
    status: str


class RuntimeAgentRunAsyncStatusResponse(BaseModel):
    job_id: str
    run_id: str = ""
    thread_id: str = ""
    status: str
    message: str = ""
    stage: str = ""
    stages: list[AgentRunStageMetadata] = Field(default_factory=list)
    decomposition_sub_questions: list[str] = Field(default_factory=list)
    sub_question_artifacts: list["SubQuestionArtifacts"] = Field(default_factory=list)
    sub_qa: list[SubQuestionAnswer] = Field(default_factory=list)
    output: str = ""
    result: RuntimeAgentRunResponse | None = None
    error: str | None = None
    cancel_requested: bool = False
    started_at: float | None = None
    finished_at: float | None = None
    elapsed_ms: int | None = None


class RuntimeAgentRunAsyncCancelResponse(BaseModel):
    status: Literal["success"]
    message: str


class RuntimeAgentInfo(BaseModel):
    agent_name: str


class GraphRunMetadata(BaseModel):
    run_id: str
    thread_id: str = ""
    trace_id: str = ""
    correlation_id: str = ""


class CitationSourceRow(BaseModel):
    citation_index: int = Field(ge=1)
    rank: int = Field(ge=1)
    title: str = ""
    source: str = ""
    content: str = ""
    document_id: str = ""
    score: float | None = None


class SubQuestionArtifacts(BaseModel):
    sub_question: str
    expanded_queries: list[str] = Field(default_factory=list)
    retrieved_docs: list[CitationSourceRow] = Field(default_factory=list)
    retrieval_provenance: list[dict[str, Any]] = Field(default_factory=list)
    reranked_docs: list[CitationSourceRow] = Field(default_factory=list)
    sub_answer: str = ""
    citation_rows_by_index: dict[int, CitationSourceRow] = Field(default_factory=dict)


class AgentGraphState(BaseModel):
    main_question: str
    decomposition_sub_questions: list[str] = Field(default_factory=list)
    sub_question_artifacts: list[SubQuestionArtifacts] = Field(default_factory=list)
    final_answer: str = ""
    citation_rows_by_index: dict[int, CitationSourceRow] = Field(default_factory=dict)
    run_metadata: GraphRunMetadata
    sub_qa: list[SubQuestionAnswer] = Field(default_factory=list)
    output: str = ""
    stage_snapshots: list["GraphStageSnapshot"] = Field(default_factory=list)


class DecomposeNodeInput(BaseModel):
    main_question: str
    run_metadata: GraphRunMetadata
    initial_search_context: list[dict[str, Any]] = Field(default_factory=list)


class DecomposeNodeOutput(BaseModel):
    decomposition_sub_questions: list[str] = Field(default_factory=list)


class ExpandNodeInput(BaseModel):
    main_question: str
    sub_question: str
    run_metadata: GraphRunMetadata


class ExpandNodeOutput(BaseModel):
    expanded_queries: list[str] = Field(default_factory=list)


class SearchNodeInput(BaseModel):
    sub_question: str
    expanded_queries: list[str] = Field(default_factory=list)
    run_metadata: GraphRunMetadata


class SearchNodeOutput(BaseModel):
    retrieved_docs: list[CitationSourceRow] = Field(default_factory=list)
    retrieval_provenance: list[dict[str, Any]] = Field(default_factory=list)
    citation_rows_by_index: dict[int, CitationSourceRow] = Field(default_factory=dict)


class RerankNodeInput(BaseModel):
    sub_question: str
    expanded_query: str = ""
    retrieved_docs: list[CitationSourceRow] = Field(default_factory=list)
    run_metadata: GraphRunMetadata


class RerankNodeOutput(BaseModel):
    reranked_docs: list[CitationSourceRow] = Field(default_factory=list)
    citation_rows_by_index: dict[int, CitationSourceRow] = Field(default_factory=dict)


class AnswerSubquestionNodeInput(BaseModel):
    sub_question: str
    reranked_docs: list[CitationSourceRow] = Field(default_factory=list)
    citation_rows_by_index: dict[int, CitationSourceRow] = Field(default_factory=dict)
    run_metadata: GraphRunMetadata


class AnswerSubquestionNodeOutput(BaseModel):
    sub_answer: str = ""
    citation_indices_used: list[int] = Field(default_factory=list)
    answerable: bool = False
    verification_reason: str = ""
    citation_rows_by_index: dict[int, CitationSourceRow] = Field(default_factory=dict)


class SynthesizeFinalNodeInput(BaseModel):
    main_question: str
    sub_qa: list[SubQuestionAnswer] = Field(default_factory=list)
    sub_question_artifacts: list[SubQuestionArtifacts] = Field(default_factory=list)
    run_metadata: GraphRunMetadata


class SynthesizeFinalNodeOutput(BaseModel):
    final_answer: str = ""


class GraphStageSnapshot(BaseModel):
    stage: str
    status: str = "completed"
    sub_question: str = ""
    lane_index: int = 0
    lane_total: int = 0
    decomposition_sub_questions: list[str] = Field(default_factory=list)
    sub_qa: list[SubQuestionAnswer] = Field(default_factory=list)
    sub_question_artifacts: list[SubQuestionArtifacts] = Field(default_factory=list)
    output: str = ""
