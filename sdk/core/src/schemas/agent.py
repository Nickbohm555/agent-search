from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Union
from uuid import UUID

from pydantic import AliasChoices
from pydantic import BaseModel, ConfigDict, Field
from pydantic import field_validator
from pydantic import model_validator


class RuntimeRerankControl(BaseModel):
    enabled: bool | None = None


class RuntimeQueryExpansionControl(BaseModel):
    enabled: bool | None = None


class RuntimeSubquestionHitlControl(BaseModel):
    enabled: bool = False


class RuntimeHitlControl(BaseModel):
    enabled: bool = False
    subquestions: RuntimeSubquestionHitlControl | None = None

    @model_validator(mode="after")
    def normalize_enabled(self) -> "RuntimeHitlControl":
        if self.subquestions is not None and self.subquestions.enabled:
            self.enabled = True
        return self


class RuntimeAgentRunControls(BaseModel):
    rerank: RuntimeRerankControl | None = None
    query_expansion: RuntimeQueryExpansionControl | None = None
    hitl: RuntimeHitlControl | None = None


class RuntimeAgentRunRuntimeConfig(BaseModel):
    rerank: RuntimeRerankControl | None = None
    query_expansion: RuntimeQueryExpansionControl | None = None


class RuntimeCustomPrompts(BaseModel):
    model_config = ConfigDict(extra="ignore")

    subanswer: str | None = None
    synthesis: str | None = None


class RuntimeAgentRunRequest(BaseModel):
    query: str = Field(min_length=1)
    thread_id: str | None = None
    checkpoint_db_url: str | None = None
    controls: RuntimeAgentRunControls | None = None
    runtime_config: RuntimeAgentRunRuntimeConfig | None = None
    custom_prompts: RuntimeCustomPrompts | None = Field(
        default=None,
        validation_alias=AliasChoices("custom_prompts", "custom-prompts"),
    )

    @field_validator("thread_id")
    @classmethod
    def validate_thread_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return str(UUID(normalized))


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
    thread_id: str | None = None
    sub_items: list[tuple[str, str]] = Field(default_factory=list)
    output: str
    final_citations: list["CitationSourceRow"] = Field(default_factory=list)


class HitlResumeDecision(BaseModel):
    item_id: str = Field(min_length=1)
    action: Literal["approve", "edit", "reject"]
    replacement_text: str | None = None

    @model_validator(mode="after")
    def validate_replacement_text(self) -> "HitlResumeDecision":
        if self.action == "edit":
            if self.replacement_text is None or not self.replacement_text.strip():
                raise ValueError("replacement_text is required when action='edit'.")
            self.replacement_text = self.replacement_text.strip()
            return self
        if self.replacement_text is not None:
            self.replacement_text = self.replacement_text.strip() or None
        return self


class HitlReviewItem(BaseModel):
    item_id: str = Field(min_length=1)
    text: str
    index: int = Field(ge=0)

    def approve(self) -> HitlResumeDecision:
        return HitlResumeDecision(item_id=self.item_id, action="approve")

    def edit(self, replacement_text: str) -> HitlResumeDecision:
        return HitlResumeDecision(item_id=self.item_id, action="edit", replacement_text=replacement_text)

    def reject(self) -> HitlResumeDecision:
        return HitlResumeDecision(item_id=self.item_id, action="reject")


class HitlReview(BaseModel):
    kind: Literal["subquestion_review"]
    stage: str = ""
    thread_id: str | None = None
    checkpoint_id: str = Field(min_length=1)
    items: list[HitlReviewItem] = Field(default_factory=list)

    @classmethod
    def from_interrupt_payload(cls, payload: Any) -> "HitlReview":
        if not isinstance(payload, Mapping):
            raise ValueError("HITL interrupt payload must be a mapping.")
        kind = str(payload.get("kind") or "").strip()
        checkpoint_id = str(payload.get("checkpoint_id") or "").strip()
        if not kind:
            raise ValueError("HITL interrupt payload is missing kind.")
        if kind != "subquestion_review":
            raise ValueError(f"Unsupported HITL review kind '{kind}'.")
        if not checkpoint_id:
            raise ValueError("HITL interrupt payload is missing checkpoint_id.")
        return cls(
            kind=kind,
            stage=str(payload.get("stage") or ""),
            thread_id=str(payload.get("thread_id") or "").strip() or None,
            checkpoint_id=checkpoint_id,
            items=cls._normalize_items(kind=kind, payload=payload),
        )

    @staticmethod
    def _normalize_items(*, kind: str, payload: Mapping[str, Any]) -> list[HitlReviewItem]:
        raw_items_key = "subquestions"
        raw_items = payload.get(raw_items_key)
        if not isinstance(raw_items, Sequence) or isinstance(raw_items, (str, bytes, bytearray)):
            return []
        item_id_key = "subquestion_id"
        text_key = "sub_question"
        items: list[HitlReviewItem] = []
        for index, raw_item in enumerate(raw_items):
            if not isinstance(raw_item, Mapping):
                continue
            raw_index = raw_item.get("index")
            items.append(
                HitlReviewItem(
                    item_id=str(raw_item.get(item_id_key) or f"item-{index + 1}").strip(),
                    text=str(raw_item.get(text_key) or "").strip(),
                    index=raw_index if isinstance(raw_index, int) and raw_index >= 0 else index,
                )
            )
        return items

    def approve_all(self) -> "HitlResumeRequest":
        return HitlResumeRequest(
            thread_id=self.thread_id,
            checkpoint_id=self.checkpoint_id,
            review_kind=self.kind,
            decisions=[item.approve() for item in self.items],
        )

    def with_decisions(self, *decisions: HitlResumeDecision) -> "HitlResumeRequest":
        return HitlResumeRequest(
            thread_id=self.thread_id,
            checkpoint_id=self.checkpoint_id,
            review_kind=self.kind,
            decisions=list(decisions),
        )


class HitlResumeRequest(BaseModel):
    thread_id: str | None = None
    checkpoint_id: str = Field(min_length=1)
    review_kind: Literal["subquestion_review"]
    decisions: list[HitlResumeDecision] = Field(min_length=1)

    @classmethod
    def approve(cls, review: HitlReview, item_id: str) -> "HitlResumeRequest":
        return review.with_decisions(HitlResumeDecision(item_id=item_id, action="approve"))

    @classmethod
    def edit(cls, review: HitlReview, item_id: str, replacement_text: str) -> "HitlResumeRequest":
        return review.with_decisions(
            HitlResumeDecision(item_id=item_id, action="edit", replacement_text=replacement_text)
        )

    @classmethod
    def reject(cls, review: HitlReview, item_id: str) -> "HitlResumeRequest":
        return review.with_decisions(HitlResumeDecision(item_id=item_id, action="reject"))


class RuntimeAgentRunResult(BaseModel):
    status: Literal["completed", "paused"]
    checkpoint_id: str | None = None
    review: HitlReview | None = Field(
        default=None,
        validation_alias=AliasChoices("review", "interrupt_payload"),
    )
    response: RuntimeAgentRunResponse | None = None

    @field_validator("review", mode="before")
    @classmethod
    def validate_review(cls, value: Any) -> HitlReview | Any | None:
        if value is None or isinstance(value, HitlReview):
            return value
        if isinstance(value, Mapping):
            return HitlReview.from_interrupt_payload(value)
        return value


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
    sub_items: list[tuple[str, str]] = Field(default_factory=list)
    output: str = ""
    result: RuntimeAgentRunResponse | None = None
    error: str | None = None
    cancel_requested: bool = False
    review: HitlReview | None = Field(
        default=None,
        validation_alias=AliasChoices("review", "interrupt_payload"),
    )
    checkpoint_id: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    elapsed_ms: int | None = None

    @field_validator("review", mode="before")
    @classmethod
    def validate_review(cls, value: Any) -> HitlReview | Any | None:
        if value is None or isinstance(value, HitlReview):
            return value
        if isinstance(value, Mapping):
            return HitlReview.from_interrupt_payload(value)
        return value

class RuntimeAgentRunAsyncCancelResponse(BaseModel):
    status: Literal["success"]
    message: str


class RuntimeSubquestionDecision(BaseModel):
    subquestion_id: str = Field(min_length=1)
    action: Literal["approve", "edit", "deny", "skip"]
    edited_text: str | None = None

    @model_validator(mode="after")
    def validate_edit_payload(self) -> "RuntimeSubquestionDecision":
        if self.action == "edit":
            if self.edited_text is None or not self.edited_text.strip():
                raise ValueError("edited_text is required when action='edit'.")
        elif self.edited_text is not None:
            self.edited_text = self.edited_text.strip() or None
        return self


class RuntimeSubquestionResumeEnvelope(BaseModel):
    thread_id: str | None = None
    checkpoint_id: str = Field(min_length=1)
    decisions: list[RuntimeSubquestionDecision] = Field(min_length=1)


class RuntimeAgentRunResumeRequest(BaseModel):
    resume: Union[
        bool,
        HitlResumeRequest,
        dict[str, Any],
        RuntimeSubquestionResumeEnvelope,
    ] = True

    @field_validator("resume", mode="before")
    @classmethod
    def validate_resume(cls, value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, HitlResumeRequest):
            return value
        if not isinstance(value, dict):
            raise ValueError(
                "resume must be a boolean, SDK HITL resume request, legacy object payload, or typed decision envelope."
            )
        if "review_kind" in value and "checkpoint_id" in value and "decisions" in value:
            return HitlResumeRequest.model_validate(value)
        if "checkpoint_id" in value or "decisions" in value:
            return RuntimeSubquestionResumeEnvelope.model_validate(value)
        return value


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
    citation_rows_by_index: dict[int, CitationSourceRow] = Field(default_factory=dict)


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
