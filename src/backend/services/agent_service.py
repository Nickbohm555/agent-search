from contextlib import nullcontext
from typing import Any, Optional

from agents.factory import build_default_agent
from schemas import RuntimeAgentInfo, RuntimeAgentRunRequest, RuntimeAgentRunResponse
from utils.query_decomposition import decompose_query


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
    with _start_agent_span(tracing_handle, payload.query) as span:
        output = agent.run(payload.query)
        span.update(
            input={"query": payload.query},
            output={"response": output},
            metadata={"agent_name": agent.name, "sub_queries": sub_queries},
        )
    return RuntimeAgentRunResponse(
        agent_name=agent.name,
        output=output,
        sub_queries=sub_queries,
    )
