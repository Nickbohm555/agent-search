from typing import Literal

from pydantic import BaseModel, Field

from .agent import RuntimeAgentRunRequest, RuntimeAgentRunResponse


class McpToolDefinition(BaseModel):
    name: Literal["agent.run"]
    description: str
    input_schema: dict[str, object] = Field(default_factory=dict)


class McpToolsListResponse(BaseModel):
    tools: list[McpToolDefinition] = Field(default_factory=list)


class McpToolInvokeRequest(BaseModel):
    tool_name: Literal["agent.run"]
    arguments: RuntimeAgentRunRequest


class McpToolInvokeResponse(BaseModel):
    tool_name: Literal["agent.run"]
    content: str
    run: RuntimeAgentRunResponse
