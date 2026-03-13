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


def _event(*, sequence: int, event_type: str, stage: str, status: str) -> RuntimeLifecycleEvent:
    return RuntimeLifecycleEvent(
        event_type=event_type,
        event_id=f"run-123:{sequence:06d}",
        run_id="run-123",
        thread_id="550e8400-e29b-41d4-a716-446655440000",
        trace_id="trace-123",
        stage=stage,
        status=status,
        emitted_at="2026-03-12T23:30:00+00:00",
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


def test_run_events_stream_returns_sse_payloads_with_lifecycle_contract() -> None:
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
        _event(sequence=2, event_type="stage.started", stage="decompose", status="running"),
        _event(sequence=3, event_type="run.completed", stage="decompose", status="success"),
    ]
    with jobs_module._JOB_LOCK:
        jobs_module._JOBS[job.job_id] = job

    response = client.get("/api/agents/run-events/job-123")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    messages = _parse_sse_messages(response.text)
    assert [message["id"] for message in messages] == [
        "run-123:000001",
        "run-123:000002",
        "run-123:000003",
    ]
    assert [message["event"] for message in messages] == [
        "run.started",
        "stage.started",
        "run.completed",
    ]
    assert messages[1]["data"] == job.lifecycle_events[1].model_dump(mode="json")


def test_run_events_stream_honors_last_event_id_header() -> None:
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
        _event(sequence=2, event_type="stage.started", stage="decompose", status="running"),
        _event(sequence=3, event_type="run.completed", stage="decompose", status="success"),
    ]
    with jobs_module._JOB_LOCK:
        jobs_module._JOBS[job.job_id] = job

    response = client.get(
        "/api/agents/run-events/job-123",
        headers={"Last-Event-ID": "run-123:000002"},
    )

    assert response.status_code == 200
    assert _parse_sse_messages(response.text) == [
        {
            "id": "run-123:000003",
            "event": "run.completed",
            "data": job.lifecycle_events[2].model_dump(mode="json"),
        }
    ]


def test_run_events_stream_returns_404_for_unknown_job() -> None:
    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.get("/api/agents/run-events/job-missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found."}


def test_iter_agent_run_events_drains_terminal_event_after_status_flip(monkeypatch) -> None:
    from agent_search.runtime import jobs as jobs_module

    job = AgentRunJobStatus(
        job_id="job-123",
        run_id="run-123",
        thread_id="550e8400-e29b-41d4-a716-446655440000",
        status="running",
    )
    started_event = _event(sequence=1, event_type="stage.completed", stage="final", status="completed")
    terminal_event = _event(sequence=2, event_type="run.completed", stage="final", status="success")
    job.lifecycle_events = [started_event]

    with jobs_module._JOB_LOCK:
        jobs_module._JOBS[job.job_id] = job

    original_list_agent_run_events = jobs_module.list_agent_run_events
    call_count = 0

    def fake_list_agent_run_events(job_id: str, *, after_event_id: str | None = None):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            with jobs_module._JOB_LOCK:
                tracked_job = jobs_module._JOBS[job_id]
                tracked_job.status = "success"
                tracked_job.lifecycle_events.append(terminal_event)
            return []
        return original_list_agent_run_events(job_id, after_event_id=after_event_id)

    monkeypatch.setattr(jobs_module, "list_agent_run_events", fake_list_agent_run_events)

    streamed_events = list(jobs_module.iter_agent_run_events(job.job_id, poll_interval=0))

    assert [event.event_type for event in streamed_events] == [
        "stage.completed",
        "run.completed",
    ]
