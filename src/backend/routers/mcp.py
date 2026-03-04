from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from db import get_db
from schemas import (
    McpRpcRequest,
    McpRpcResponse,
    McpToolInvokeRequest,
    McpToolInvokeResponse,
    McpToolsListResponse,
)
from services.mcp_service import handle_mcp_rpc, invoke_mcp_tool, list_mcp_tools

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


@router.post("/rpc", response_model=McpRpcResponse)
def invoke_mcp_rpc(
    payload: McpRpcRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> McpRpcResponse:
    """Handle MCP-compatible JSON-RPC methods for tool discovery and execution."""
    return handle_mcp_rpc(payload, db=db, tracing_handle=request.app.state.langfuse)
