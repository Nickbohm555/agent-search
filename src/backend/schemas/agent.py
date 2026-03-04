from typing import Literal

from pydantic import BaseModel, Field

from .web import WebToolRun


class RuntimeAgentInfo(BaseModel):
    name: str
    version: str


class RuntimeAgentRunRequest(BaseModel):
    query: str = Field(min_length=1)


class SubQueryToolAssignment(BaseModel):
    sub_query: str
    tool: Literal["internal", "web"]


class RuntimeAgentRunResponse(BaseModel):
    agent_name: str
    output: str
    sub_queries: list[str]
    tool_assignments: list[SubQueryToolAssignment]
    web_tool_runs: list[WebToolRun] = Field(default_factory=list)
