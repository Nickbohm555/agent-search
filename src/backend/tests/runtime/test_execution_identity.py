import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime.execution_identity import (
    ExecutionIdentityError,
    mint_thread_id,
    resolve_thread_identity,
    validate_thread_id,
)
from models import RuntimeExecutionRun


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    RuntimeExecutionRun.__table__.create(engine)
    return Session(engine)


def test_validate_thread_id_rejects_blank_values() -> None:
    with pytest.raises(ExecutionIdentityError, match="thread_id must be a non-empty UUID string."):
        validate_thread_id("   ")


def test_validate_thread_id_canonicalizes_uuid_format() -> None:
    raw_thread_id = "550E8400-E29B-41D4-A716-446655440000"

    assert validate_thread_id(raw_thread_id) == "550e8400-e29b-41d4-a716-446655440000"


def test_mint_thread_id_returns_uuid_string() -> None:
    minted_thread_id = mint_thread_id()

    assert str(uuid.UUID(minted_thread_id)) == minted_thread_id


def test_resolve_thread_identity_mints_and_persists_thread_id_when_absent() -> None:
    session = _make_session()

    run = resolve_thread_identity(session=session, run_id="run-123")
    persisted = session.get(RuntimeExecutionRun, "run-123")

    assert persisted is not None
    assert run.thread_id == persisted.thread_id
    assert str(uuid.UUID(run.thread_id)) == run.thread_id
    session.close()


def test_resolve_thread_identity_persists_client_provided_thread_id() -> None:
    session = _make_session()
    thread_id = "550e8400-e29b-41d4-a716-446655440000"

    run = resolve_thread_identity(session=session, run_id="run-123", thread_id=thread_id)

    assert run.thread_id == thread_id
    session.close()


def test_resolve_thread_identity_returns_stable_thread_id_for_existing_run_lineage() -> None:
    session = _make_session()

    created = resolve_thread_identity(session=session, run_id="run-123")
    resolved = resolve_thread_identity(session=session, run_id="run-123")

    assert resolved.run_id == created.run_id
    assert resolved.thread_id == created.thread_id
    session.close()


def test_resolve_thread_identity_rejects_conflicting_thread_id_for_existing_run() -> None:
    session = _make_session()

    resolve_thread_identity(
        session=session,
        run_id="run-123",
        thread_id="550e8400-e29b-41d4-a716-446655440000",
    )

    with pytest.raises(ExecutionIdentityError, match="run_id is already bound to a different thread_id"):
        resolve_thread_identity(
            session=session,
            run_id="run-123",
            thread_id="550e8400-e29b-41d4-a716-446655440001",
        )

    session.close()


def test_resolve_thread_identity_rejects_invalid_thread_id_format() -> None:
    session = _make_session()

    with pytest.raises(ExecutionIdentityError, match="thread_id must be a valid UUID string."):
        resolve_thread_identity(session=session, run_id="run-123", thread_id="not-a-uuid")

    session.close()
