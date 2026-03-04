from typing import Any, Optional

from schemas import (
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
