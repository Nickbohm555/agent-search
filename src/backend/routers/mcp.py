from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from db import get_db
from schemas import McpToolInvokeRequest, McpToolInvokeResponse, McpToolsListResponse
from services.mcp_service import invoke_mcp_tool, list_mcp_tools

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/tools", response_model=McpToolsListResponse)
def get_mcp_tools() -> McpToolsListResponse:
    """Expose MCP-compatible tool metadata for client-side tool discovery."""
    return list_mcp_tools()


@router.post("/invoke", response_model=McpToolInvokeResponse)
def invoke_mcp(
    payload: McpToolInvokeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> McpToolInvokeResponse:
    """Invoke MCP tool calls by delegating to application runtime services."""
    return invoke_mcp_tool(payload, db=db, tracing_handle=request.app.state.langfuse)
