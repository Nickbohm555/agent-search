from typing import Any

from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP

from db import SessionLocal
from schemas import RuntimeAgentRunRequest
from services.agent_service import run_runtime_agent

_MCP_TOOL_NAME = "agent.run"
_MCP_TOOL_DESCRIPTION = "Run the orchestrated query pipeline and return a synthesized answer."


def create_fastmcp_app(app: FastAPI) -> Any:
    mcp = FastMCP(name="agent-search-mcp", stateless_http=True, json_response=True)

    @mcp.tool(name=_MCP_TOOL_NAME, description=_MCP_TOOL_DESCRIPTION)
    def run_agent(query: str) -> dict[str, Any]:
        if not query.strip():
            raise ValueError("query must be a non-empty string")

        db = SessionLocal()
        try:
            run_response = run_runtime_agent(
                RuntimeAgentRunRequest(query=query),
                db=db,
                tracing_handle=app.state.langfuse,
                runtime_handle=app.state.runtime_model,
            )
        finally:
            db.close()

        return {
            "output": run_response.output,
            "structuredContent": run_response.model_dump(),
        }

    return mcp.streamable_http_app()
