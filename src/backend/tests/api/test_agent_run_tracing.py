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


def _collect_stream_events(response) -> list[dict]:
    events: list[dict] = []
    event_name = ""
    data_json = ""
    for raw_line in response.iter_lines():
        line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
        if line.startswith("event: "):
            event_name = line.removeprefix("event: ").strip()
            continue
        if line.startswith("data: "):
            data_json = line.removeprefix("data: ").strip()
            continue
        if line == "" and data_json:
            payload = json.loads(data_json)
            payload["__sse_event_name"] = event_name
            events.append(payload)
            event_name = ""
            data_json = ""
    return events


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
    assert span_record["span"].updates == [
        {
            "input": {"query": "trace this run"},
            "output": {"response": payload["output"]},
            "metadata": {
                "agent_name": payload["agent_name"],
                "sub_queries": payload["sub_queries"],
                "tool_assignments": payload["tool_assignments"],
                "retrieval_results": payload["retrieval_results"],
                "validation_results": payload["validation_results"],
                "subquery_execution_results": payload["subquery_execution_results"],
                "web_tool_runs": payload["web_tool_runs"],
            },
        }
    ]


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
def test_agent_run_stream_creates_trace_when_enabled(client):
    tracing_handle = _EnabledTracingHandle()
    client.app.state.langfuse = tracing_handle

    with client.stream(
        "POST",
        "/api/agents/run/stream",
        json={"query": "stream trace this run"},
    ) as response:
        assert response.status_code == 200
        events = _collect_stream_events(response)

    assert events[-1]["event"] == "completed"
    completed_output = events[-1]["data"]["output"]
    assert len(tracing_handle.span_records) == 1
    span_record = tracing_handle.span_records[0]
    assert span_record["name"] == "agent.run"
    assert span_record["kwargs"]["input"] == {"query": "stream trace this run"}
    assert span_record["span"].updates[-1]["output"] == {"response": completed_output}


@pytest.mark.smoke
def test_mcp_tools_call_creates_trace_when_enabled(client):
    tracing_handle = _EnabledTracingHandle()
    client.app.state.langfuse = tracing_handle

    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {
                "name": "agent.run",
                "arguments": {"query": "mcp trace this run"},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["isError"] is False
    assert len(tracing_handle.span_records) == 1
    span_record = tracing_handle.span_records[0]
    assert span_record["name"] == "agent.run"
    assert span_record["kwargs"]["input"] == {"query": "mcp trace this run"}
    assert span_record["span"].updates[-1]["output"] == {
        "response": payload["result"]["content"][0]["text"]
    }
