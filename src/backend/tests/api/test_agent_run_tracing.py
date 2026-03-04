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
