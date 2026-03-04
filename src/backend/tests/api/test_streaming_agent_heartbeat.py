import json

import pytest


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
    assert any(item["event"] == "retrieval_result" for item in events[:-1])
    assert any(item["event"] == "validation_result" for item in events[:-1])
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
