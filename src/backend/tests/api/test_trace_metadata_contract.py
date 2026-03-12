from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime.jobs import AgentRunJobStatus
from agent_search.runtime.lifecycle_events import RuntimeLifecycleEvent
from routers.agent import router as agent_router
from schemas import RuntimeAgentRunAsyncStatusResponse


def _event(*, sequence: int, event_type: str, stage: str, status: str, error: str | None = None) -> RuntimeLifecycleEvent:
    return RuntimeLifecycleEvent(
        event_type=event_type,
        event_id=f"run-123:{sequence:06d}",
        run_id="run-123",
        thread_id="550e8400-e29b-41d4-a716-446655440000",
        trace_id="trace-123",
        stage=stage,
        status=status,
        emitted_at="2026-03-12T23:30:00+00:00",
        error=error,
    )


def _parse_sse_messages(body: str) -> list[dict[str, object]]:
    messages: list[dict[str, object]] = []
    for chunk in body.strip().split("\n\n"):
        if not chunk.strip():
            continue
        message: dict[str, object] = {}
        for line in chunk.splitlines():
            prefix, _, value = line.partition(": ")
            if prefix == "data":
                message[prefix] = json.loads(value)
            else:
                message[prefix] = value
        messages.append(message)
    return messages


@pytest.fixture(autouse=True)
def clear_jobs():
    from agent_search.runtime import jobs as jobs_module

    with jobs_module._JOB_LOCK:
        jobs_module._JOBS.clear()
    yield
    with jobs_module._JOB_LOCK:
        jobs_module._JOBS.clear()


def test_trace_metadata_contract_keeps_joinable_tuple_across_successful_run_event_payloads() -> None:
    from agent_search.runtime import jobs as jobs_module

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    job = AgentRunJobStatus(
        job_id="job-123",
        run_id="run-123",
        thread_id="550e8400-e29b-41d4-a716-446655440000",
        status="success",
    )
    job.lifecycle_events = [
        _event(sequence=1, event_type="run.started", stage="runtime", status="running"),
        _event(sequence=2, event_type="stage.started", stage="search", status="running"),
        _event(sequence=3, event_type="run.completed", stage="search", status="success"),
    ]
    with jobs_module._JOB_LOCK:
        jobs_module._JOBS[job.job_id] = job

    response = client.get("/api/agents/run-events/job-123")

    assert response.status_code == 200
    messages = _parse_sse_messages(response.text)
    assert {
        (message["data"]["run_id"], message["data"]["thread_id"], message["data"]["trace_id"])
        for message in messages
    } == {
        ("run-123", "550e8400-e29b-41d4-a716-446655440000", "trace-123")
    }
    assert messages[-1]["event"] == "run.completed"
    assert messages[-1]["data"]["status"] == "success"


def test_trace_metadata_contract_keeps_joinable_tuple_across_failed_run_status_and_event_payloads(monkeypatch) -> None:
    from agent_search.runtime import jobs as jobs_module
    from routers import agent as agent_router_module

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    job = AgentRunJobStatus(
        job_id="job-123",
        run_id="run-123",
        thread_id="550e8400-e29b-41d4-a716-446655440000",
        status="error",
    )
    job.lifecycle_events = [
        _event(sequence=1, event_type="run.started", stage="runtime", status="running"),
        _event(sequence=2, event_type="stage.failed", stage="search", status="error", error="provider timeout"),
        _event(sequence=3, event_type="run.failed", stage="search", status="error", error="provider timeout"),
    ]
    with jobs_module._JOB_LOCK:
        jobs_module._JOBS[job.job_id] = job

    monkeypatch.setattr(
        agent_router_module,
        "sdk_get_run_status",
        lambda _job_id: RuntimeAgentRunAsyncStatusResponse(
            job_id="job-123",
            run_id="run-123",
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            status="error",
            message="Failed.",
            stage="search",
            error="provider timeout",
        ),
    )

    events_response = client.get("/api/agents/run-events/job-123")
    status_response = client.get("/api/agents/run-status/job-123")

    assert events_response.status_code == 200
    assert status_response.status_code == 200

    messages = _parse_sse_messages(events_response.text)
    assert {
        (message["data"]["run_id"], message["data"]["thread_id"], message["data"]["trace_id"])
        for message in messages
    } == {
        ("run-123", "550e8400-e29b-41d4-a716-446655440000", "trace-123")
    }
    assert status_response.json()["run_id"] == messages[-1]["data"]["run_id"]
    assert status_response.json()["thread_id"] == messages[-1]["data"]["thread_id"]
    assert messages[-1]["event"] == "run.failed"
    assert messages[-1]["data"]["status"] == "error"
    assert messages[-1]["data"]["error"] == "provider timeout"
