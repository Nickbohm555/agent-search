from pydantic import BaseModel, Field


class RuntimeAgentRunRequest(BaseModel):
    query: str = Field(min_length=1)


class RuntimeAgentRunResponse(BaseModel):
    output: str
