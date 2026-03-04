import json
import time

import pytest
from schemas import RuntimeAgentRunResponse


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
def test_agent_run_stream_emits_progress_events_before_completion(client):
    with client.stream(
        "POST",
        "/api/agents/run/stream",
        json={"query": "compare our internal launch note with current web updates"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        events = _collect_stream_events(response)

    assert events
    assert all(item["sequence"] == idx + 1 for idx, item in enumerate(events))
    assert events[-1]["event"] == "completed"
    assert events[-1]["__sse_event_name"] == "completed"
    assert any(item["event"] == "sub_queries" for item in events[:-1])
    assert any(item["event"] == "heartbeat" for item in events[:-1])
    assert any(item["event"] == "subquery_execution_result" for item in events[:-1])
    assert any(item["event"] == "retrieval_result" for item in events[:-1])
    assert any(item["event"] == "validation_result" for item in events[:-1])
    execution_event = next(item for item in events if item["event"] == "subquery_execution_result")
    assert "validation_result" in execution_event["data"]
    assert "attempt_trace" in execution_event["data"]["validation_result"]
    assert isinstance(events[-1]["data"]["output"], str)
    assert events[-1]["data"]["output"].strip() != ""


@pytest.mark.smoke
def test_agent_run_stream_allows_client_disconnect_without_server_error(client):
    with client.stream(
        "POST",
        "/api/agents/run/stream",
        json={"query": "stream disconnect behavior"},
    ) as response:
        assert response.status_code == 200
        iterator = response.iter_lines()
        first_line = next(iterator)
        if isinstance(first_line, bytes):
            first_line = first_line.decode("utf-8")
        assert first_line.startswith("event: ")


@pytest.mark.smoke
def test_agent_run_stream_emits_first_event_before_run_finishes(client, monkeypatch):
    def fake_run_runtime_agent(*_args, **kwargs):
        callback = kwargs.get("stream_event_callback")
        if callback is not None:
            callback(
                "heartbeat",
                {"step": "decomposition", "status": "started", "details": {}},
            )
        time.sleep(0.35)
        return RuntimeAgentRunResponse(
            agent_name="agent-search-default",
            output="Synthetic final answer",
            sub_queries=["synthetic-subquery"],
            tool_assignments=[],
            retrieval_results=[],
            validation_results=[],
            subquery_execution_results=[],
            web_tool_runs=[],
            graph_state=None,
        )

    monkeypatch.setattr("routers.agent.run_runtime_agent", fake_run_runtime_agent)

    with client.stream(
        "POST",
        "/api/agents/run/stream",
        json={"query": "timing check"},
    ) as response:
        assert response.status_code == 200
        started_at = time.monotonic()
        first_data_line = None
        for raw_line in response.iter_lines():
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if line.startswith("data: "):
                first_data_line = line
                break
        elapsed = time.monotonic() - started_at

    assert first_data_line is not None
    assert elapsed < 0.25
    first_event = json.loads(first_data_line.removeprefix("data: ").strip())
    assert first_event["event"] == "heartbeat"


@pytest.mark.smoke
def test_agent_run_stream_emits_error_event_when_runtime_fails(client, monkeypatch):
    def fake_run_runtime_agent(*_args, **_kwargs):
        raise RuntimeError("intentional stream failure")

    monkeypatch.setattr("routers.agent.run_runtime_agent", fake_run_runtime_agent)

    with client.stream(
        "POST",
        "/api/agents/run/stream",
        json={"query": "error path check"},
    ) as response:
        assert response.status_code == 200
        events = _collect_stream_events(response)

    assert events
    assert events[-1]["event"] == "error"
    assert events[-1]["__sse_event_name"] == "error"
    assert "intentional stream failure" in events[-1]["data"]["message"]
