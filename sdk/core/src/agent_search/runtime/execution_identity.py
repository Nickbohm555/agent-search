from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from models import RuntimeExecutionRun


class ExecutionIdentityError(ValueError):
    """Raised when runtime thread identity inputs are invalid or inconsistent."""


def _normalize_run_id(run_id: str) -> str:
    normalized_run_id = run_id.strip()
    if not normalized_run_id:
        raise ExecutionIdentityError("run_id must be a non-empty string.")
    return normalized_run_id


def validate_thread_id(thread_id: str) -> str:
    normalized_thread_id = thread_id.strip()
    if not normalized_thread_id:
        raise ExecutionIdentityError("thread_id must be a non-empty UUID string.")

    try:
        parsed_thread_id = uuid.UUID(normalized_thread_id)
    except ValueError as exc:
        raise ExecutionIdentityError("thread_id must be a valid UUID string.") from exc
    return str(parsed_thread_id)


def mint_thread_id() -> str:
    return str(uuid.uuid4())


def resolve_thread_identity(
    *,
    session: Session,
    run_id: str,
    thread_id: str | None = None,
    status: str = "pending",
    metadata: dict[str, Any] | None = None,
) -> RuntimeExecutionRun:
    normalized_run_id = _normalize_run_id(run_id)
    normalized_thread_id = validate_thread_id(thread_id) if thread_id is not None else None

    existing_run = session.get(RuntimeExecutionRun, normalized_run_id)
    if existing_run is not None:
        if normalized_thread_id is not None and existing_run.thread_id != normalized_thread_id:
            raise ExecutionIdentityError(
                "run_id is already bound to a different thread_id: "
                f"{existing_run.thread_id} != {normalized_thread_id}"
            )
        return existing_run

    resolved_thread_id = normalized_thread_id or mint_thread_id()
    run = RuntimeExecutionRun(
        run_id=normalized_run_id,
        thread_id=resolved_thread_id,
        status=status,
        metadata_json=dict(metadata or {}),
    )
    session.add(run)
    session.flush()
    return run


__all__ = [
    "ExecutionIdentityError",
    "mint_thread_id",
    "resolve_thread_identity",
    "validate_thread_id",
]
