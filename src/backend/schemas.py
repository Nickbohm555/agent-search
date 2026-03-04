from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class DocumentCreate(BaseModel):
    title: str
    content: str
    embedding: list[float] = Field(min_length=1536, max_length=1536)


class DocumentOut(BaseModel):
    id: int
    title: str
    content: str


class SimilarityQuery(BaseModel):
    embedding: list[float] = Field(min_length=1536, max_length=1536)
    k: int = Field(default=5, ge=1, le=50)


class AgentPlanRequest(BaseModel):
    query: str = Field(min_length=1)


class AgentSubquery(BaseModel):
    id: int
    text: str = Field(min_length=1)
    tool: Literal["internal_rag", "web_search"]


class AgentProgressEvent(BaseModel):
    step: Literal["decomposition", "tool_selection"]
    status: Literal["completed"]
    detail: str = Field(min_length=1)


class AgentPlanResponse(BaseModel):
    query: str
    trajectory: list[Literal["decomposition", "tool_selection"]]
    subqueries: list[AgentSubquery]
    events: list[AgentProgressEvent]
