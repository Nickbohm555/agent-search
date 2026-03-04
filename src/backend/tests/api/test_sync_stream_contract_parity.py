import json
from uuid import uuid4

import pytest


def _extract_stream_events(raw_body: str) -> list[dict]:
    """Parse SSE `data:` lines emitted by `/api/agents/run/stream` into event dicts."""
    events: list[dict] = []
    for line in raw_body.splitlines():
        if not line.startswith("data: "):
            continue
        events.append(json.loads(line[len("data: ") :]))
    return events


@pytest.mark.smoke
def test_runtime_agent_run_contract_stays_stable(client):
    """Ensure `/api/agents/run` keeps the required response keys for downstream consumers."""
    response = client.post("/api/agents/run", json={"query": "contract stability query"})

    assert response.status_code == 200
    data = response.json()
    required_fields = {
        "sub_queries",
        "tool_assignments",
        "retrieval_results",
        "validation_results",
        "output",
        "graph_state",
        "thread_id",
    }
    assert required_fields.issubset(data.keys())
    assert "checkpoint_id" in data
    assert isinstance(data["sub_queries"], list)
    assert isinstance(data["tool_assignments"], list)
    assert isinstance(data["retrieval_results"], list)
    assert isinstance(data["validation_results"], list)
    assert isinstance(data["output"], str)
    assert data["output"].strip() != ""
    assert isinstance(data["thread_id"], str)
    assert data["thread_id"].strip() != ""


@pytest.mark.smoke
def test_runtime_agent_stream_completed_payload_matches_sync_final_values(client):
    """Verify stream completion payload parity with sync endpoint final values for one payload."""
    thread_id = f"thread-parity-{uuid4()}"
    payload = {
        "query": "parity deterministic query for sync and stream",
        "thread_id": thread_id,
        "user_id": "parity-user",
    }

    sync_response = client.post("/api/agents/run", json=payload)
    stream_response = client.post("/api/agents/run/stream", json=payload)

    assert sync_response.status_code == 200
    assert stream_response.status_code == 200

    sync_data = sync_response.json()
    stream_events = _extract_stream_events(stream_response.text)
    completed_event = next(item for item in stream_events if item["event"] == "completed")
    completed_data = completed_event["data"]

    assert completed_data["output"] == sync_data["output"]
    assert completed_data["sub_queries"] == sync_data["sub_queries"]
    assert completed_data["tool_assignments"] == sync_data["tool_assignments"]
    assert completed_data["thread_id"] == sync_data["thread_id"]
    assert completed_data["thread_id"] == thread_id
