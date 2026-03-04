from contextlib import nullcontext
from typing import Any, Optional

from agents.factory import build_default_agent
from schemas import (
    RuntimeAgentInfo,
    RuntimeAgentRunRequest,
    RuntimeAgentRunResponse,
    SubQueryToolAssignment,
    WebToolRun,
)
from services.web_service import run_web_search_then_open
from utils.query_decomposition import decompose_query
from utils.tool_selection import assign_tools_to_sub_queries


def get_runtime_agent_info() -> RuntimeAgentInfo:
    agent = build_default_agent()
    return RuntimeAgentInfo(name=agent.name, version=agent.version)


class _NoOpSpan:
    def update(self, **_: Any) -> None:
        return None


def _start_agent_span(tracing_handle: Any, query: str) -> Any:
    if not getattr(tracing_handle, "enabled", False):
        return nullcontext(_NoOpSpan())

    if not hasattr(tracing_handle, "start_as_current_span"):
        return nullcontext(_NoOpSpan())

    return tracing_handle.start_as_current_span(
        name="agent.run",
        input={"query": query},
    )


def run_runtime_agent(
    payload: RuntimeAgentRunRequest,
    tracing_handle: Optional[Any] = None,
) -> RuntimeAgentRunResponse:
    agent = build_default_agent()
    sub_queries = decompose_query(payload.query)
    tool_assignments = [
        SubQueryToolAssignment(sub_query=sub_query, tool=tool)
        for sub_query, tool in assign_tools_to_sub_queries(sub_queries)
    ]
    web_tool_runs: list[WebToolRun] = []
    for assignment in tool_assignments:
        if assignment.tool != "web":
            continue
        web_tool_runs.append(run_web_search_then_open(assignment.sub_query))

    with _start_agent_span(tracing_handle, payload.query) as span:
        output = agent.run(payload.query)
        span.update(
            input={"query": payload.query},
            output={"response": output},
            metadata={
                "agent_name": agent.name,
                "sub_queries": sub_queries,
                "tool_assignments": [
                    assignment.model_dump() for assignment in tool_assignments
                ],
                "web_tool_runs": [run.model_dump() for run in web_tool_runs],
            },
        )
    return RuntimeAgentRunResponse(
        agent_name=agent.name,
        output=output,
        sub_queries=sub_queries,
        tool_assignments=tool_assignments,
        web_tool_runs=web_tool_runs,
    )
