from typing import Any, Literal

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


class McpRpcRequest(BaseModel):
    """JSON-RPC request payload accepted by MCP-compatible route handlers."""

    jsonrpc: Literal["2.0"]
    id: str | int | None = None
    method: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class McpRpcError(BaseModel):
    """JSON-RPC error payload emitted for unsupported MCP method calls."""

    code: int
    message: str


class McpRpcResultToolsList(BaseModel):
    """Result payload for `tools/list` MCP method."""

    tools: list[McpToolDefinition] = Field(default_factory=list)


class McpRpcCallContent(BaseModel):
    """MCP `tools/call` content block carrying synthesized agent text."""

    type: Literal["text"] = "text"
    text: str


class McpRpcResultToolCall(BaseModel):
    """Result payload for `tools/call` with text + structured run metadata."""

    content: list[McpRpcCallContent] = Field(default_factory=list)
    structured_content: McpToolInvokeResponse = Field(alias="structuredContent")
    is_error: bool = Field(default=False, alias="isError")

    model_config = {"populate_by_name": True}


class McpRpcInitializeResult(BaseModel):
    """Result payload for MCP `initialize` capability negotiation."""

    protocol_version: str = Field(default="2025-03-26", alias="protocolVersion")
    capabilities: dict[str, dict[str, object]] = Field(default_factory=lambda: {"tools": {}})
    server_info: dict[str, str] = Field(
        default_factory=lambda: {"name": "agent-search-mcp", "version": "0.1.0"},
        alias="serverInfo",
    )

    model_config = {"populate_by_name": True}


class McpRpcResponse(BaseModel):
    """JSON-RPC response shape for MCP-compatible methods."""

    jsonrpc: Literal["2.0"] = "2.0"
    id: str | int | None = None
    result: dict[str, Any] | None = None
    error: McpRpcError | None = None
