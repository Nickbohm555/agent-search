from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from agent_search.errors import SDKConfigurationError
from agent_search.runtime import jobs as jobs_module
from agent_search.runtime import persistence
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from models import RuntimeExecutionRun


class _FakeResult:
    def __init__(self, schema_ready: bool) -> None:
        self._schema_ready = schema_ready

    def fetchone(self) -> dict[str, bool]:
        return {"schema_ready": self._schema_ready}


class _FakeCursor:
    def __init__(self, schema_ready: bool) -> None:
        self._schema_ready = schema_ready

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _ = exc_type, exc, tb

    def execute(self, _query: str) -> _FakeResult:
        return _FakeResult(self._schema_ready)


class _FakeCheckpointer:
    def __init__(self, *, schema_ready: bool) -> None:
        self._schema_ready = schema_ready
        self.setup_calls = 0
        self.serde = None

    def _cursor(self) -> _FakeCursor:
        return _FakeCursor(self._schema_ready)

    def setup(self) -> None:
        self.setup_calls += 1


@pytest.fixture(autouse=True)
def clear_bootstrapped_connections() -> None:
    persistence._BOOTSTRAPPED_CONNECTIONS.clear()


def test_get_checkpointer_connection_string_requires_explicit_database_url() -> None:
    with pytest.raises(SDKConfigurationError, match="checkpoint_db_url is required"):
        persistence.get_checkpointer_connection_string(None)


def test_bootstrap_checkpointer_skips_setup_when_schema_exists() -> None:
    checkpointer = _FakeCheckpointer(schema_ready=True)

    persistence._bootstrap_checkpointer(checkpointer, connection_string="postgresql://checkpoint-db")

    assert checkpointer.setup_calls == 0


def test_bootstrap_checkpointer_runs_setup_when_schema_missing() -> None:
    checkpointer = _FakeCheckpointer(schema_ready=False)

    persistence._bootstrap_checkpointer(checkpointer, connection_string="postgresql://checkpoint-db")

    assert checkpointer.setup_calls == 1


def test_ready_checkpointer_installs_allowlisted_msgpack_serde(monkeypatch) -> None:
    checkpointer = _FakeCheckpointer(schema_ready=True)

    class _FakeConnection:
        def __enter__(self) -> "_FakeConnection":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            _ = exc_type, exc, tb

    monkeypatch.setattr(
        persistence.Connection,
        "connect",
        lambda *_args, **_kwargs: _FakeConnection(),
    )
    monkeypatch.setattr(
        persistence,
        "PostgresSaver",
        lambda *_args, serde=None, **_kwargs: _attach_serde(checkpointer, serde),
    )

    with persistence.ready_checkpointer(database_url="postgresql://checkpoint-db") as ready:
        assert ready is checkpointer

    assert isinstance(checkpointer.serde, JsonPlusSerializer)
    assert set(checkpointer.serde._allowed_msgpack_modules) == set(persistence._CHECKPOINT_MSGPACK_ALLOWLIST)


def _attach_serde(checkpointer: _FakeCheckpointer, serde: JsonPlusSerializer | None) -> _FakeCheckpointer:
    checkpointer.serde = serde
    return checkpointer


def test_restore_agent_run_job_rehydrates_paused_job_from_persisted_runtime_row(monkeypatch) -> None:
    class _FakeSession:
        def get(self, model, key):
            assert model is RuntimeExecutionRun
            assert key == "job-restore"
            return RuntimeExecutionRun(
                run_id="job-restore",
                thread_id="550e8400-e29b-41d4-a716-446655440055",
                status="paused",
                started_at=datetime(2026, 3, 12, 23, 30, tzinfo=timezone.utc),
                completed_at=None,
                error_message=None,
                metadata_json={
                    "job_id": "job-restore",
                    "stage": "subquestions_ready",
                    "message": "Paused and awaiting resume input.",
                    "query": "Resume me",
                    "request_payload": {
                        "query": "Resume me",
                        "checkpoint_db_url": "postgresql://checkpoint-db",
                        "controls": {"hitl": {"enabled": True, "subquestions": {"enabled": True}}},
                    },
                    "interrupt_payload": {
                        "kind": "subquestion_review",
                        "checkpoint_id": "checkpoint-live",
                        "subquestions": [{"subquestion_id": "sq-1", "sub_question": "What changed?"}],
                    },
                    "checkpoint_id": "checkpoint-live",
                },
            )

        def close(self) -> None:
            return None

    monkeypatch.setattr(jobs_module, "SessionLocal", lambda: _FakeSession())
    with jobs_module._JOB_LOCK:
        jobs_module._JOBS.clear()

    restored = jobs_module.restore_agent_run_job("job-restore", model="model", vector_store="vector-store")

    assert restored is not None
    assert restored.job_id == "job-restore"
    assert restored.run_id == "job-restore"
    assert restored.status == "paused"
    assert restored.stage == "subquestions_ready"
    assert restored.checkpoint_id == "checkpoint-live"
    assert restored.runtime_model == "model"
    assert restored.runtime_vector_store == "vector-store"
    assert restored.lifecycle_event_sequence == 1_000_000

    resumed_event = jobs_module._build_job_lifecycle_event(
        restored,
        event_type="run.completed",
        stage="synthesize_final",
        status="success",
    )

    assert resumed_event.event_id == "job-restore:1000001"
