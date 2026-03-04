from typing import Literal

from pydantic import BaseModel, Field

from .internal_data import InternalRetrievedChunk
from .web import WebOpenUrlResponse, WebSearchResult, WebToolRun


class RuntimeAgentInfo(BaseModel):
    name: str
    version: str


class RuntimeAgentRunRequest(BaseModel):
    query: str = Field(min_length=1)


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


class RuntimeAgentRunResponse(BaseModel):
    agent_name: str
    output: str
    sub_queries: list[str]
    tool_assignments: list[SubQueryToolAssignment]
    retrieval_results: list[SubQueryRetrievalResult] = Field(default_factory=list)
    validation_results: list[SubQueryValidationResult] = Field(default_factory=list)
    web_tool_runs: list[WebToolRun] = Field(default_factory=list)
