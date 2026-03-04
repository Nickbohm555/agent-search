from contextlib import nullcontext
from typing import Any, Optional

from agents.factory import AgentFactory, build_default_agent
from schemas import (
    RuntimeAgentInfo,
    RuntimeAgentRunRequest,
    RuntimeAgentRunResponse,
    RuntimeAgentStreamEvent,
    WebToolRun,
)
from sqlalchemy.orm import Session


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
    db: Session,
    tracing_handle: Optional[Any] = None,
    runtime_handle: Optional[Any] = None,
) -> RuntimeAgentRunResponse:
    factory = AgentFactory(runtime_handle=runtime_handle)
    agent = build_default_agent()
    graph_agent = factory.create_langgraph_agent()
    graph_result = graph_agent.run(payload.query, db)
    sub_queries = graph_result["sub_queries"]
    tool_assignments = graph_result["tool_assignments"]
    retrieval_results = graph_result["retrieval_results"]
    validation_results = graph_result["validation_results"]
    subquery_execution_results = graph_result["subquery_execution_results"]
    output = graph_result["output"]
    graph_state = graph_result["graph_state"]
    web_tool_runs: list[WebToolRun] = [
        WebToolRun(
            sub_query=result.sub_query,
            search_results=result.web_search_results,
            opened_urls=result.opened_urls,
            opened_pages=result.opened_pages,
        )
        for result in retrieval_results
        if result.tool == "web"
    ]

    with _start_agent_span(tracing_handle, payload.query) as span:
        span.update(
            input={"query": payload.query},
            output={"response": output},
            metadata={
                "agent_name": agent.name,
                "sub_queries": sub_queries,
                "tool_assignments": [
                    assignment.model_dump() for assignment in tool_assignments
                ],
                "retrieval_results": [result.model_dump() for result in retrieval_results],
                "validation_results": [result.model_dump() for result in validation_results],
                "subquery_execution_results": [
                    result.model_dump() for result in subquery_execution_results
                ],
                "web_tool_runs": [run.model_dump() for run in web_tool_runs],
            },
        )
    return RuntimeAgentRunResponse(
        agent_name=agent.name,
        output=output,
        sub_queries=sub_queries,
        tool_assignments=tool_assignments,
        retrieval_results=retrieval_results,
        validation_results=validation_results,
        subquery_execution_results=subquery_execution_results,
        web_tool_runs=web_tool_runs,
        graph_state=graph_state,
    )


def build_runtime_agent_stream_events(
    response: RuntimeAgentRunResponse,
) -> list[RuntimeAgentStreamEvent]:
    events: list[RuntimeAgentStreamEvent] = []
    sequence = 1

    def append_event(event: str, data: dict[str, Any]) -> None:
        nonlocal sequence
        events.append(RuntimeAgentStreamEvent(sequence=sequence, event=event, data=data))
        sequence += 1

    if response.graph_state is not None:
        for item in response.graph_state.timeline:
            append_event(
                "heartbeat",
                {
                    "step": item.step,
                    "status": item.status,
                    "details": item.details,
                },
            )

    append_event("sub_queries", {"sub_queries": response.sub_queries})
    append_event(
        "tool_assignments",
        {"tool_assignments": [item.model_dump() for item in response.tool_assignments]},
    )
    for item in response.subquery_execution_results:
        append_event("subquery_execution_result", item.model_dump())
    for item in response.retrieval_results:
        append_event("retrieval_result", item.model_dump())
    for item in response.validation_results:
        append_event("validation_result", item.model_dump())
    append_event(
        "completed",
        {
            "agent_name": response.agent_name,
            "output": response.output,
            "graph_state": response.graph_state.model_dump()
            if response.graph_state is not None
            else None,
        },
    )
    return events
