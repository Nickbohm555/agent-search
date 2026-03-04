from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from db import get_db
from schemas import MCPJsonRpcRequest, RuntimeAgentRunRequest
from services.agent_service import run_runtime_agent

router = APIRouter(tags=["mcp"])

_PROTOCOL_VERSION = "2024-11-05"
_TOOL_NAME = "agent.run"
_TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"query": {"type": "string", "minLength": 1}},
    "required": ["query"],
    "additionalProperties": False,
}


def _jsonrpc_result(request_id: str | int | None, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _jsonrpc_error(
    request_id: str | int | None,
    code: int,
    message: str,
) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


@router.post("/mcp")
def mcp_invoke(
    payload: MCPJsonRpcRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    method = payload.method

    if method == "initialize":
        return _jsonrpc_result(
            payload.id,
            {
                "protocolVersion": _PROTOCOL_VERSION,
                "serverInfo": {"name": "agent-search-mcp", "version": "0.1.0"},
                "capabilities": {"tools": {"listChanged": False}},
            },
        )

    if method == "tools/list":
        return _jsonrpc_result(
            payload.id,
            {
                "tools": [
                    {
                        "name": _TOOL_NAME,
                        "description": (
                            "Run the orchestrated query pipeline and return a synthesized answer."
                        ),
                        "inputSchema": _TOOL_SCHEMA,
                    }
                ]
            },
        )

    if method != "tools/call":
        return _jsonrpc_error(payload.id, -32601, f"Method not found: {method}")

    tool_name = payload.params.get("name")
    if tool_name != _TOOL_NAME:
        return _jsonrpc_error(payload.id, -32601, f"Unknown tool: {tool_name}")

    arguments = payload.params.get("arguments")
    if not isinstance(arguments, dict):
        return _jsonrpc_error(payload.id, -32602, "Invalid params: arguments must be an object.")

    query = arguments.get("query")
    if not isinstance(query, str) or not query.strip():
        return _jsonrpc_error(payload.id, -32602, "Invalid params: query must be a non-empty string.")

    run_response = run_runtime_agent(
        RuntimeAgentRunRequest(query=query),
        db=db,
        tracing_handle=request.app.state.langfuse,
        runtime_handle=request.app.state.runtime_model,
    )
    structured_content = run_response.model_dump()
    return _jsonrpc_result(
        payload.id,
        {
            "content": [{"type": "text", "text": run_response.output}],
            "structuredContent": structured_content,
            "isError": False,
        },
    )

