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
from schemas import GraphStageSnapshot, RuntimeAgentRunControls, RuntimeAgentRunRequest, RuntimeHitlControl, RuntimeSubquestionHitlControl


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


def test_checkpoint_route_switches_to_subquestion_gate_when_hitl_enabled() -> None:
    from agent_search.runtime.graph.routes import route_post_decompose
    from agent_search.runtime.graph.state import to_runtime_graph_state
    from services.agent_service import build_graph_run_metadata

    state = to_runtime_graph_state(
        RuntimeAgentRunRequest(
            query="Main question?",
            controls=RuntimeAgentRunControls(
                hitl=RuntimeHitlControl(
                    enabled=True,
                    subquestions=RuntimeSubquestionHitlControl(enabled=True),
                )
            ),
        ),
        run_metadata=build_graph_run_metadata(run_id="run-checkpoint-route"),
    )
    state["decomposition_sub_questions"] = ["Sub-question A?", "Sub-question B?"]

    assert route_post_decompose(state) == "subquestion_checkpoint"


def test_checkpoint_enabled_initial_run_pauses_at_subquestions_ready(monkeypatch) -> None:
    from agent_search.runtime import jobs as jobs_module

    monkeypatch.setattr(jobs_module, "_persist_job_status", lambda _job: None)
    monkeypatch.setattr(
        jobs_module,
        "execute_runtime_graph",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("non-checkpoint path should not execute")),
    )

    payload = RuntimeAgentRunRequest(
        query="Review these subquestions",
        thread_id="550e8400-e29b-41d4-a716-446655440111",
        controls=RuntimeAgentRunControls(
            hitl=RuntimeHitlControl(
                enabled=True,
                subquestions=RuntimeSubquestionHitlControl(enabled=True),
            )
        ),
    )
    job = AgentRunJobStatus(
        job_id="job-hitl",
        run_id="run-hitl",
        thread_id=payload.thread_id or "",
        status="running",
        query=payload.query,
        request_payload=payload.model_dump(mode="json", exclude_none=True),
        runtime_model=object(),
        runtime_vector_store=object(),
    )

    with jobs_module._JOB_LOCK:
        jobs_module._JOBS[job.job_id] = job

    def fake_run_checkpointed_agent(*, snapshot_callback=None, **_kwargs):
        if snapshot_callback is not None:
            snapshot_callback(
                GraphStageSnapshot(
                    stage="decompose",
                    status="completed",
                    decomposition_sub_questions=["Keep this?", "Change this?"],
                    sub_qa=[],
                    sub_question_artifacts=[],
                    output="",
                ),
                {
                    "main_question": payload.query,
                    "decomposition_sub_questions": ["Keep this?", "Change this?"],
                    "sub_question_artifacts": [],
                    "final_answer": "",
                    "citation_rows_by_index": {},
                    "run_metadata": {"run_id": "run-hitl", "thread_id": payload.thread_id},
                    "sub_qa": [],
                    "output": "",
                    "stage_snapshots": [],
                },
            )
        return type(
            "PausedOutcome",
            (),
            {
                "status": "paused",
                "state": None,
                "response": None,
                "interrupt_payload": {
                    "checkpoint_id": "checkpoint-42",
                    "kind": "subquestion_review",
                    "stage": "subquestions_ready",
                    "subquestions": [
                        {"subquestion_id": "sq-1", "sub_question": "Keep this?"},
                        {"subquestion_id": "sq-2", "sub_question": "Change this?"},
                    ],
                },
                "checkpoint_id": "checkpoint-42",
            },
        )()

    monkeypatch.setattr(jobs_module, "run_checkpointed_agent", fake_run_checkpointed_agent)

    jobs_module._run_agent_job(
        job.job_id,
        payload,
        job.run_id,
        job.thread_id,
        job.runtime_model,
        job.runtime_vector_store,
    )

    tracked_job = jobs_module.get_agent_run_job(job.job_id)
    assert tracked_job is not None
    assert tracked_job.status == "paused"
    assert tracked_job.stage == "subquestions_ready"
    assert tracked_job.decomposition_sub_questions == ["Keep this?", "Change this?"]
    assert tracked_job.checkpoint_id == "checkpoint-42"
    assert tracked_job.lifecycle_events[-1].event_type == "run.paused"
    assert tracked_job.lifecycle_events[-1].stage == "subquestions_ready"


def test_non_checkpoint_initial_run_bypasses_pause_path_when_hitl_disabled(monkeypatch) -> None:
    from agent_search.runtime import jobs as jobs_module
    from services.agent_service import build_graph_run_metadata

    monkeypatch.setattr(jobs_module, "_persist_job_status", lambda _job: None)
    monkeypatch.setattr(
        jobs_module,
        "run_checkpointed_agent",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("checkpoint path should not execute")),
    )

    payload = RuntimeAgentRunRequest(
        query="Run without HITL",
        thread_id="550e8400-e29b-41d4-a716-446655440112",
    )
    job = AgentRunJobStatus(
        job_id="job-non-hitl",
        run_id="run-non-hitl",
        thread_id=payload.thread_id or "",
        status="running",
        query=payload.query,
        request_payload=payload.model_dump(mode="json", exclude_none=True),
        runtime_model=object(),
        runtime_vector_store=object(),
    )

    with jobs_module._JOB_LOCK:
        jobs_module._JOBS[job.job_id] = job

    def fake_execute_runtime_graph(*, context, run_metadata, snapshot_callback=None, **_kwargs):
        if snapshot_callback is not None:
            snapshot_callback(
                GraphStageSnapshot(
                    stage="decompose",
                    status="completed",
                    decomposition_sub_questions=["Only subquestion?"],
                    sub_qa=[],
                    sub_question_artifacts=[],
                    output="",
                ),
                {
                    "main_question": context.payload.query,
                    "decomposition_sub_questions": ["Only subquestion?"],
                    "sub_question_artifacts": [],
                    "final_answer": "",
                    "citation_rows_by_index": {},
                    "run_metadata": build_graph_run_metadata(run_id=run_metadata.run_id, thread_id=run_metadata.thread_id),
                    "sub_qa": [],
                    "output": "Completed without pause.",
                    "stage_snapshots": [],
                },
            )
        return {
            "main_question": context.payload.query,
            "decomposition_sub_questions": ["Only subquestion?"],
            "sub_question_artifacts": [],
            "final_answer": "Completed without pause.",
            "citation_rows_by_index": {},
            "run_metadata": build_graph_run_metadata(run_id=run_metadata.run_id, thread_id=run_metadata.thread_id),
            "sub_qa": [],
            "output": "Completed without pause.",
            "stage_snapshots": [],
        }

    monkeypatch.setattr(jobs_module, "execute_runtime_graph", fake_execute_runtime_graph)

    jobs_module._run_agent_job(
        job.job_id,
        payload,
        job.run_id,
        job.thread_id,
        job.runtime_model,
        job.runtime_vector_store,
    )

    tracked_job = jobs_module.get_agent_run_job(job.job_id)
    assert tracked_job is not None
    assert tracked_job.status == "success"
    assert tracked_job.stage == "subquestions_ready"
    assert tracked_job.checkpoint_id is None
    assert tracked_job.lifecycle_events[-1].event_type == "run.completed"
