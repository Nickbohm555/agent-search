import json
from typing import Any, Optional

import pytest
from sqlalchemy.orm import Session

from schemas import RuntimeAgentRunRequest, RuntimeAgentRunResponse, RuntimeAgentStreamEvent
from services import agent_service


def _extract_stream_events(raw_body: str) -> list[dict]:
    events: list[dict] = []
    for line in raw_body.splitlines():
        if not line.startswith("data: "):
            continue
        events.append(json.loads(line[len("data: ") :]))
    return events


@pytest.mark.smoke
def test_runtime_stream_compiles_once_across_consecutive_requests(client):
    agent_service._reset_stream_runtime_cache_for_tests()
    assert agent_service._get_stream_runtime_compile_count_for_tests() == 0

    first = client.post("/api/agents/run/stream", json={"query": "compile once first"})
    second = client.post("/api/agents/run/stream", json={"query": "compile once second"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert agent_service._get_stream_runtime_compile_count_for_tests() == 1


@pytest.mark.smoke
def test_runtime_stream_calls_astream_and_ainvoke_with_deterministic_fallback_events(client, monkeypatch):
    agent_service._reset_stream_runtime_cache_for_tests()

    class FakeCompiledRuntime:
        def __init__(self) -> None:
            self.astream_calls = 0
            self.ainvoke_calls = 0

        async def astream(
            self,
            *,
            payload: RuntimeAgentRunRequest,
            db: Session,
            tracing_handle: Optional[Any],
        ) -> list[RuntimeAgentStreamEvent]:
            del payload, db, tracing_handle
            self.astream_calls += 1
            return []

        async def ainvoke(
            self,
            *,
            payload: RuntimeAgentRunRequest,
            db: Session,
            tracing_handle: Optional[Any],
        ) -> RuntimeAgentRunResponse:
            self.ainvoke_calls += 1
            return agent_service.run_runtime_agent(payload, db=db, tracing_handle=tracing_handle)

    fake_runtime = FakeCompiledRuntime()
    monkeypatch.setattr(agent_service, "_compile_stream_runtime", lambda: fake_runtime)

    response = client.post("/api/agents/run/stream", json={"query": "dummy fallback stream"})

    assert response.status_code == 200
    events = _extract_stream_events(response.text)
    event_names = [item["event"] for item in events]
    assert event_names[:4] == ["heartbeat", "progress", "sub_queries", "completed"]
    assert fake_runtime.astream_calls == 1
    assert fake_runtime.ainvoke_calls == 1

    completed_event = next(item for item in events if item["event"] == "completed")
    assert completed_event["data"]["agent_name"] != ""
    assert completed_event["data"]["output"] != ""
    assert completed_event["data"]["thread_id"] != ""
    assert "graph_state" not in completed_event["data"]
