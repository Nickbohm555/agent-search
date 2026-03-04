from typing import Any, Optional

from schemas import (
    McpRpcError,
    McpRpcRequest,
    McpRpcResponse,
    McpToolDefinition,
    McpToolInvokeRequest,
    McpToolInvokeResponse,
    McpToolsListResponse,
)
from services.agent_service import run_runtime_agent
from sqlalchemy.orm import Session


def list_mcp_tools() -> McpToolsListResponse:
    """Return MCP-exposed tools and stable invocation schema metadata."""
    tool = McpToolDefinition(
        name="agent.run",
        description="Run the runtime agent pipeline for one query and return the synthesized answer.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "thread_id": {"type": "string"},
                "user_id": {"type": "string"},
                "checkpoint_id": {"type": "string"},
            },
            "required": ["query"],
        },
    )
    return McpToolsListResponse(tools=[tool])


def invoke_mcp_tool(
    payload: McpToolInvokeRequest,
    db: Session,
    tracing_handle: Optional[Any] = None,
) -> McpToolInvokeResponse:
    """Invoke one MCP tool by delegating to the runtime agent execution boundary."""
    run_response = run_runtime_agent(payload.arguments, db=db, tracing_handle=tracing_handle)
    return McpToolInvokeResponse(
        tool_name=payload.tool_name,
        content=run_response.output,
        run=run_response,
    )


def handle_mcp_rpc(
    payload: McpRpcRequest,
    db: Session,
    tracing_handle: Optional[Any] = None,
) -> McpRpcResponse:
    """Handle MCP-compatible JSON-RPC requests for tool discovery and invocation.

    Called by `routers/mcp.py::invoke_mcp_rpc` to expose an MCP-style method
    surface (`initialize`, `tools/list`, `tools/call`) while reusing the
    existing runtime tool delegation implemented in this service.
    """
    if payload.method == "initialize":
        return McpRpcResponse(
            id=payload.id,
            result={
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "agent-search-mcp", "version": "0.1.0"},
            },
        )

    if payload.method == "tools/list":
        tools = list_mcp_tools()
        return McpRpcResponse(
            id=payload.id,
            result={
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema,
                    }
                    for tool in tools.tools
                ]
            },
        )

    if payload.method == "tools/call":
        tool_name = payload.params.get("name")
        arguments = payload.params.get("arguments")
        if tool_name != "agent.run" or not isinstance(arguments, dict):
            return McpRpcResponse(
                id=payload.id,
                error=McpRpcError(code=-32602, message="Invalid params for tools/call"),
            )

        invoke_payload = McpToolInvokeRequest(tool_name=tool_name, arguments=arguments)
        invoke_response = invoke_mcp_tool(invoke_payload, db=db, tracing_handle=tracing_handle)
        return McpRpcResponse(
            id=payload.id,
            result={
                "content": [{"type": "text", "text": invoke_response.content}],
                "structuredContent": invoke_response.model_dump(),
                "isError": False,
            },
        )

    return McpRpcResponse(
        id=payload.id,
        error=McpRpcError(code=-32601, message=f"Method not found: {payload.method}"),
    )
