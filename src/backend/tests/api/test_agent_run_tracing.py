import json

import pytest


class _FakeSpan:
    def __init__(self) -> None:
        self.updates: list[dict] = []

    def update(self, **kwargs) -> None:
        self.updates.append(kwargs)


class _FakeSpanContextManager:
    def __init__(self, span: _FakeSpan) -> None:
        self._span = span

    def __enter__(self) -> _FakeSpan:
        return self._span

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _EnabledTracingHandle:
    def __init__(self) -> None:
        self.enabled = True
        self.span_records: list[dict] = []

    def start_as_current_span(self, name: str, **kwargs):
        span = _FakeSpan()
        record = {"name": name, "kwargs": kwargs, "span": span}
        self.span_records.append(record)
        return _FakeSpanContextManager(span)


class _DisabledTracingHandle:
    def __init__(self) -> None:
        self.enabled = False
        self.calls = 0

    def start_as_current_span(self, name: str, **kwargs):
        self.calls += 1
        raise AssertionError("Disabled tracing handle should not be used.")


def _extract_completed_event(raw_body: str) -> dict:
    """Return the `completed` SSE event payload from one streamed run response body."""
    for line in raw_body.splitlines():
        if not line.startswith("data: "):
            continue
        payload = json.loads(line[len("data: ") :])
        if payload.get("event") == "completed":
            return payload
    raise AssertionError("Expected one completed event in stream body.")


@pytest.mark.smoke
def test_agent_run_creates_trace_with_query_agent_and_output_when_enabled(client):
    tracing_handle = _EnabledTracingHandle()
    client.app.state.langfuse = tracing_handle

    response = client.post("/api/agents/run", json={"query": "trace this run"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["agent_name"] != ""
    assert payload["output"] != ""
    assert payload["sub_queries"] == ["trace this run"]
    assert payload["tool_assignments"] == [
        {"sub_query": "trace this run", "tool": "internal"}
    ]
    assert len(payload["retrieval_results"]) == 1
    assert payload["retrieval_results"][0]["tool"] == "internal"
    assert len(payload["validation_results"]) == 1
    assert payload["validation_results"][0]["tool"] == "internal"

    assert len(tracing_handle.span_records) == 1
    span_record = tracing_handle.span_records[0]
    assert span_record["name"] == "agent.run"
    assert span_record["kwargs"]["input"] == {"query": "trace this run"}
    assert span_record["span"].updates == [{
        "input": {"query": "trace this run"},
        "output": {"response": payload["output"]},
        "metadata": {
            "agent_name": payload["agent_name"],
            "sub_queries": payload["sub_queries"],
            "tool_assignments": payload["tool_assignments"],
            "retrieval_results": payload["retrieval_results"],
            "validation_results": payload["validation_results"],
            "web_tool_runs": payload["web_tool_runs"],
            "persistence_context": {
                "thread_id": payload["thread_id"],
                "checkpoint_id": payload["graph_state"]["graph"]["execution"]["persistence"][
                    "resolved_checkpoint_id"
                ],
                "user_id": "anonymous",
            },
        },
    }]


@pytest.mark.smoke
def test_agent_run_trace_metadata_includes_explicit_persistence_fields(client):
    tracing_handle = _EnabledTracingHandle()
    client.app.state.langfuse = tracing_handle

    response = client.post(
        "/api/agents/run",
        json={
            "query": "trace explicit persistence",
            "thread_id": "thread-tracing-1",
            "user_id": "trace-user-1",
            "checkpoint_id": "checkpoint-tracing-1",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["thread_id"] == "thread-tracing-1"
    assert payload["checkpoint_id"] == "checkpoint-tracing-1"

    assert len(tracing_handle.span_records) == 1
    metadata = tracing_handle.span_records[0]["span"].updates[0]["metadata"]
    assert metadata["persistence_context"] == {
        "thread_id": "thread-tracing-1",
        "checkpoint_id": "checkpoint-tracing-1",
        "user_id": "trace-user-1",
    }


@pytest.mark.smoke
def test_agent_run_with_disabled_tracing_returns_response_without_trace_creation(client):
    tracing_handle = _DisabledTracingHandle()
    client.app.state.langfuse = tracing_handle

    response = client.post("/api/agents/run", json={"query": "still works"})

    assert response.status_code == 200
    assert response.json()["agent_name"] != ""
    assert response.json()["output"] != ""
    assert response.json()["sub_queries"] == ["still works"]
    assert response.json()["tool_assignments"] == [
        {"sub_query": "still works", "tool": "internal"}
    ]
    assert response.json()["retrieval_results"][0]["tool"] == "internal"
    assert response.json()["validation_results"][0]["tool"] == "internal"
    assert tracing_handle.calls == 0


@pytest.mark.smoke
def test_agent_run_failure_still_records_error_trace_when_enabled(client, monkeypatch):
    tracing_handle = _EnabledTracingHandle()
    client.app.state.langfuse = tracing_handle

    class _FailingGraphAgent:
        def run(self, *_args, **_kwargs):
            raise RuntimeError("simulated runtime failure")

    monkeypatch.setattr(
        "services.agent_service.AgentFactory.create_langgraph_agent",
        lambda _self: _FailingGraphAgent(),
    )

    with pytest.raises(RuntimeError, match="simulated runtime failure"):
        client.post(
            "/api/agents/run",
            json={
                "query": "trace failing run",
                "thread_id": "trace-failure-thread",
                "user_id": "trace-failure-user",
            },
        )

    assert len(tracing_handle.span_records) == 1
    span_record = tracing_handle.span_records[0]
    assert span_record["name"] == "agent.run"
    assert span_record["kwargs"]["input"] == {"query": "trace failing run"}
    assert span_record["span"].updates == [{
        "input": {"query": "trace failing run"},
        "output": {"error": "simulated runtime failure"},
        "metadata": {
            "agent_name": "agent-search-default",
            "status": "error",
            "error_type": "RuntimeError",
            "persistence_context": {
                "thread_id": "trace-failure-thread",
                "checkpoint_id": None,
                "user_id": "trace-failure-user",
            },
        },
    }]


@pytest.mark.smoke
def test_consecutive_agent_runs_create_distinct_spans_when_enabled(client):
    tracing_handle = _EnabledTracingHandle()
    client.app.state.langfuse = tracing_handle

    first_response = client.post("/api/agents/run", json={"query": "first"})
    second_response = client.post("/api/agents/run", json={"query": "second"})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(tracing_handle.span_records) == 2

    first_span = tracing_handle.span_records[0]["span"]
    second_span = tracing_handle.span_records[1]["span"]
    assert first_span is not second_span
    assert tracing_handle.span_records[0]["kwargs"]["input"] == {"query": "first"}
    assert tracing_handle.span_records[1]["kwargs"]["input"] == {"query": "second"}


@pytest.mark.smoke
def test_agent_run_stream_delegates_to_traced_runtime_execution_when_enabled(client):
    tracing_handle = _EnabledTracingHandle()
    client.app.state.langfuse = tracing_handle

    response = client.post("/api/agents/run/stream", json={"query": "trace streamed run"})

    assert response.status_code == 200
    completed_event = _extract_completed_event(response.text)

    assert len(tracing_handle.span_records) == 1
    span_record = tracing_handle.span_records[0]
    assert span_record["name"] == "agent.run"
    assert span_record["kwargs"]["input"] == {"query": "trace streamed run"}

    metadata = span_record["span"].updates[0]["metadata"]
    assert metadata["agent_name"] == completed_event["data"]["agent_name"]
    assert metadata["sub_queries"] == completed_event["data"]["sub_queries"]
    assert metadata["persistence_context"]["thread_id"] == completed_event["data"]["thread_id"]


@pytest.mark.smoke
def test_mcp_invoke_delegates_to_traced_runtime_execution_when_enabled(client):
    tracing_handle = _EnabledTracingHandle()
    client.app.state.langfuse = tracing_handle

    response = client.post(
        "/api/mcp/invoke",
        json={
            "tool_name": "agent.run",
            "arguments": {
                "query": "trace mcp delegated run",
                "thread_id": "mcp-trace-thread",
                "user_id": "mcp-trace-user",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert len(tracing_handle.span_records) == 1
    span_record = tracing_handle.span_records[0]
    assert span_record["name"] == "agent.run"
    assert span_record["kwargs"]["input"] == {"query": "trace mcp delegated run"}

    metadata = span_record["span"].updates[0]["metadata"]
    assert metadata["agent_name"] == payload["run"]["agent_name"]
    assert metadata["sub_queries"] == payload["run"]["sub_queries"]
    resolved_checkpoint_id = payload["run"]["graph_state"]["graph"]["execution"]["persistence"][
        "resolved_checkpoint_id"
    ]
    assert metadata["persistence_context"] == {
        "thread_id": "mcp-trace-thread",
        "checkpoint_id": resolved_checkpoint_id,
        "user_id": "mcp-trace-user",
    }
