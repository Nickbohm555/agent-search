from pydantic import BaseModel, Field


class RuntimeAgentInfo(BaseModel):
    name: str
    version: str


class RuntimeAgentRunRequest(BaseModel):
    query: str = Field(min_length=1)


class RuntimeAgentRunResponse(BaseModel):
    agent_name: str
    output: str
    sub_queries: list[str]
