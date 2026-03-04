from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from .internal_data import InternalRetrievedChunk
from .web import WebOpenUrlResponse, WebSearchResult, WebToolRun


class RuntimeAgentInfo(BaseModel):
    name: str
    version: str


class RuntimeAgentRunRequest(BaseModel):
    query: str = Field(min_length=1)
    thread_id: Optional[str] = Field(default=None, min_length=1)
    user_id: Optional[str] = Field(default=None, min_length=1)
    checkpoint_id: Optional[str] = Field(default=None, min_length=1)


class SubQueryToolAssignment(BaseModel):
    sub_query: str
    tool: Literal["internal", "web"]


class SubQueryRetrievalResult(BaseModel):
    sub_query: str
    tool: Literal["internal", "web"]
    internal_results: list[InternalRetrievedChunk] = Field(default_factory=list)
    web_search_results: list[WebSearchResult] = Field(default_factory=list)
    opened_urls: list[str] = Field(default_factory=list)
    opened_pages: list[WebOpenUrlResponse] = Field(default_factory=list)


class SubQueryValidationResult(BaseModel):
    sub_query: str
    tool: Literal["internal", "web"]
    sufficient: bool
    status: Literal["validated", "stopped_insufficient"]
    attempts: int = Field(ge=1)
    follow_up_actions: list[str] = Field(default_factory=list)
    stop_reason: str


class RuntimeAgentGraphStep(BaseModel):
    step: str
    status: Literal["started", "completed"]
    details: dict[str, Any] = Field(default_factory=dict)


class RuntimeAgentGraphState(BaseModel):
    current_step: str
    timeline: list[RuntimeAgentGraphStep] = Field(default_factory=list)
    graph: dict[str, Any] = Field(default_factory=dict)


class RuntimeAgentStreamEvent(BaseModel):
    sequence: int = Field(ge=1)
    event: Literal[
        "heartbeat",
        "sub_queries",
        "tool_assignments",
        "retrieval_result",
        "validation_result",
        "completed",
    ]
    data: dict[str, Any] = Field(default_factory=dict)


class RuntimeAgentRunResponse(BaseModel):
    agent_name: str
    output: str
    thread_id: str = Field(min_length=1)
    checkpoint_id: Optional[str] = None
    sub_queries: list[str]
    tool_assignments: list[SubQueryToolAssignment]
    retrieval_results: list[SubQueryRetrievalResult] = Field(default_factory=list)
    validation_results: list[SubQueryValidationResult] = Field(default_factory=list)
    web_tool_runs: list[WebToolRun] = Field(default_factory=list)
    graph_state: Optional[RuntimeAgentGraphState] = None
