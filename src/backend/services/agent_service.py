from contextlib import nullcontext
from typing import Any, Optional

from agents.factory import AgentFactory, build_default_agent
from schemas import (
    RuntimeAgentInfo,
    RuntimeAgentRunRequest,
    RuntimeAgentRunResponse,
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


# THIS should return a deepagentlanggraph agent object from the frontend payload.
# for now, all agents will be configurd the same way.
def run_runtime_agent(
    payload: RuntimeAgentRunRequest,
    db: Session,
    tracing_handle: Optional[Any] = None,
) -> RuntimeAgentRunResponse:
    """Execute the runtime pipeline for `/api/agents/run`.

    Called by `routers/agent.py::runtime_agent_run` to orchestrate one request and
    return API-contract response fields. It forwards request config
    (`thread_id`/`user_id`/`checkpoint_id`) to the runtime agent and emits a
    trace span when tracing is enabled.
    """
    factory = AgentFactory()
    agent = build_default_agent()
    graph_agent = factory.create_langgraph_agent()
    graph_result = graph_agent.run(payload, db)
    sub_queries = graph_result["sub_queries"]
    tool_assignments = graph_result["tool_assignments"]
    retrieval_results = graph_result["retrieval_results"]
    validation_results = graph_result["validation_results"]
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

    # this will be using langfuse tracing....
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
                "web_tool_runs": [run.model_dump() for run in web_tool_runs],
            },
        )
    return RuntimeAgentRunResponse(
        agent_name=agent.name,
        output=output,
        thread_id=graph_result["thread_id"],
        checkpoint_id=graph_result["checkpoint_id"],
        sub_queries=sub_queries,
        tool_assignments=tool_assignments,
        retrieval_results=retrieval_results,
        validation_results=validation_results,
        web_tool_runs=web_tool_runs,
        graph_state=graph_state,
    )
