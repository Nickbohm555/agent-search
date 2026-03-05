from pydantic import BaseModel, Field


class RuntimeAgentRunRequest(BaseModel):
    query: str = Field(min_length=1)


class SubQuestionAnswer(BaseModel):
    sub_question: str
    sub_answer: str


class RuntimeAgentRunResponse(BaseModel):
    output: str


class RuntimeAgentInfo(BaseModel):
    agent_name: str
