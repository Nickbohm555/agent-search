import asyncio
from contextlib import nullcontext
from threading import Lock
from typing import Any, Awaitable, Iterator, Optional, Protocol

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


class _CompiledStreamRuntime(Protocol):
    """Compiled runtime contract used by stream execution.

    Implementations are cached once per process by `_get_or_compile_stream_runtime`.
    The stream path calls:
    - `astream` first to try runtime-native progress events.
    - `ainvoke` to obtain deterministic final response payload for completion.
    """

    async def astream(
        self,
        *,
        payload: RuntimeAgentRunRequest,
        db: Session,
        tracing_handle: Optional[Any],
    ) -> list[RuntimeAgentStreamEvent]:
        ...

    async def ainvoke(
        self,
        *,
        payload: RuntimeAgentRunRequest,
        db: Session,
        tracing_handle: Optional[Any],
    ) -> RuntimeAgentRunResponse:
        ...


class _ScaffoldCompiledStreamRuntime:
    """Scaffold compiled runtime used until runtime-native stream events are wired."""

    async def astream(
        self,
        *,
        payload: RuntimeAgentRunRequest,
        db: Session,
        tracing_handle: Optional[Any],
    ) -> list[RuntimeAgentStreamEvent]:
        """Return runtime-native stream events if available.

        Called by `stream_runtime_agent` before fallback emission. Scaffold mode
        returns no runtime stream events so deterministic fallback events are used.
        """
        del payload, db, tracing_handle
        return []

    async def ainvoke(
        self,
        *,
        payload: RuntimeAgentRunRequest,
        db: Session,
        tracing_handle: Optional[Any],
    ) -> RuntimeAgentRunResponse:
        """Return deterministic final payload for stream completion.

        Called by `stream_runtime_agent` after `astream` so completion payload stays
        contract-compatible with `/api/agents/run`.
        """
        return run_runtime_agent(payload, db=db, tracing_handle=tracing_handle)


_STREAM_RUNTIME_CACHE: Optional[_CompiledStreamRuntime] = None
_STREAM_RUNTIME_COMPILE_COUNT = 0
_STREAM_RUNTIME_CACHE_LOCK = Lock()


def _compile_stream_runtime() -> _CompiledStreamRuntime:
    """Compile/initialize runtime stream executor for process-level cache.

    Called by `_get_or_compile_stream_runtime` when no runtime has been cached in
    the current process. Scaffold returns a deterministic runtime adapter.
    """
    return _ScaffoldCompiledStreamRuntime()


def _get_or_compile_stream_runtime() -> _CompiledStreamRuntime:
    """Return process-cached compiled runtime for stream requests.

    Called by `stream_runtime_agent` on every request. Compiles only once per
    process lifecycle to avoid per-request runtime initialization overhead.
    """
    global _STREAM_RUNTIME_CACHE
    global _STREAM_RUNTIME_COMPILE_COUNT

    with _STREAM_RUNTIME_CACHE_LOCK:
        if _STREAM_RUNTIME_CACHE is None:
            _STREAM_RUNTIME_CACHE = _compile_stream_runtime()
            _STREAM_RUNTIME_COMPILE_COUNT += 1
        return _STREAM_RUNTIME_CACHE


def _reset_stream_runtime_cache_for_tests() -> None:
    """Reset stream-runtime cache for deterministic tests.

    Called by backend tests that verify compile-once behavior across consecutive
    stream requests in isolation.
    """
    global _STREAM_RUNTIME_CACHE
    global _STREAM_RUNTIME_COMPILE_COUNT

    with _STREAM_RUNTIME_CACHE_LOCK:
        _STREAM_RUNTIME_CACHE = None
        _STREAM_RUNTIME_COMPILE_COUNT = 0


def _get_stream_runtime_compile_count_for_tests() -> int:
    """Return runtime compile count observed in this process.

    Called by backend tests to assert compile/init happens once across multiple
    stream requests after cache reset.
    """
    with _STREAM_RUNTIME_CACHE_LOCK:
        return _STREAM_RUNTIME_COMPILE_COUNT


def _extract_persistence_context(
    payload: RuntimeAgentRunRequest,
    graph_result: dict[str, Any],
) -> dict[str, Optional[str]]:
    """Return trace-safe persistence identifiers for one runtime agent run.

    Called by `run_runtime_agent` when creating Langfuse span metadata so
    tracing captures deepAgent persistence context even if portions of
    graph metadata are absent.
    """
    graph_state = graph_result.get("graph_state")
    graph_payload = getattr(graph_state, "graph", {}) if graph_state else {}
    execution = graph_payload.get("execution", {})
    persistence = execution.get("persistence", {})
    resolved_checkpoint_id = persistence.get("resolved_checkpoint_id")

    return {
        "thread_id": graph_result.get("thread_id") or payload.thread_id,
        "checkpoint_id": resolved_checkpoint_id or graph_result.get("checkpoint_id"),
        "user_id": execution.get("user_id") or payload.user_id or "anonymous",
    }


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
    persistence_context = _extract_persistence_context(payload, graph_result)

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
                "persistence_context": persistence_context,
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


def _to_sse_payload(event: RuntimeAgentStreamEvent) -> str:
    """Serialize one runtime stream event as an SSE data frame."""
    return f"data: {event.model_dump_json()}\n\n"


def _await_runtime_call(awaitable: Awaitable[Any]) -> Any:
    """Synchronously resolve one runtime awaitable from stream request path."""
    return asyncio.run(awaitable)


def stream_runtime_agent(
    payload: RuntimeAgentRunRequest,
    db: Session,
    tracing_handle: Optional[Any] = None,
) -> Iterator[str]:
    """Stream deterministic run progress events as SSE frames.

    Called by `routers/agent.py::runtime_agent_run_stream`.
    Emits a heartbeat immediately, then deterministic progress, sub-query, and
    tool-assignment data before final completion derived from runtime
    `astream`/`ainvoke` entrypoints.
    """
    runtime = _get_or_compile_stream_runtime()
    sequence = 1
    yield _to_sse_payload(
        RuntimeAgentStreamEvent(
            sequence=sequence,
            event="heartbeat",
            data={"status": "started", "query": payload.query},
        )
    )

    runtime_events = _await_runtime_call(
        runtime.astream(payload=payload, db=db, tracing_handle=tracing_handle)
    )
    if runtime_events:
        for runtime_event in runtime_events:
            sequence += 1
            yield _to_sse_payload(
                RuntimeAgentStreamEvent(
                    sequence=sequence,
                    event=runtime_event.event,
                    data=runtime_event.data,
                )
            )

    run_response = _await_runtime_call(
        runtime.ainvoke(payload=payload, db=db, tracing_handle=tracing_handle)
    )

    if not runtime_events:
        sequence += 1
        yield _to_sse_payload(
            RuntimeAgentStreamEvent(
                sequence=sequence,
                event="progress",
                data={"step": "invoke_fallback", "status": "running"},
            )
        )

    sequence += 1
    yield _to_sse_payload(
        RuntimeAgentStreamEvent(
            sequence=sequence,
            event="sub_queries",
            data={
                "sub_queries": run_response.sub_queries,
                "count": len(run_response.sub_queries),
            },
        )
    )

    sequence += 1
    yield _to_sse_payload(
        RuntimeAgentStreamEvent(
            sequence=sequence,
            event="tool_assignments",
            data={
                "tool_assignments": [
                    item.model_dump() for item in run_response.tool_assignments
                ],
                "count": len(run_response.tool_assignments),
            },
        )
    )

    sequence += 1
    completed_data = {
        "agent_name": run_response.agent_name,
        "output": run_response.output,
        "thread_id": run_response.thread_id,
        "checkpoint_id": run_response.checkpoint_id,
        "sub_queries": run_response.sub_queries,
        "tool_assignments": [item.model_dump() for item in run_response.tool_assignments],
    }
    yield _to_sse_payload(
        RuntimeAgentStreamEvent(
            sequence=sequence,
            event="completed",
            data=completed_data,
        )
    )
