import json

import pytest


def _extract_stream_events(raw_body: str) -> list[dict]:
    events: list[dict] = []
    for line in raw_body.splitlines():
        if not line.startswith("data: "):
            continue
        events.append(json.loads(line[len("data: ") :]))
    return events


@pytest.mark.smoke
def test_runtime_agent_stream_endpoint_emits_ordered_heartbeat_subqueries_and_completion(client):
    response = client.post("/api/agents/run/stream", json={"query": "stream deterministic run"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _extract_stream_events(response.text)
    assert len(events) >= 3

    sequences = [item["sequence"] for item in events]
    assert sequences == sorted(sequences)
    assert len(set(sequences)) == len(sequences)

    event_names = [item["event"] for item in events]
    assert "heartbeat" in event_names
    assert "sub_queries" in event_names
    assert "completed" in event_names

    completed_event = next(item for item in events if item["event"] == "completed")
    assert completed_event["data"]["agent_name"] != ""
    assert completed_event["data"]["output"] != ""
    assert completed_event["data"]["thread_id"] != ""
