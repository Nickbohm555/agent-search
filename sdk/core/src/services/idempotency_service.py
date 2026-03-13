from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.exc import IntegrityError

from agent_search.runtime.execution_identity import resolve_thread_identity
from db import SessionLocal
from models import RuntimeIdempotencyEffect


class IdempotencyReplayError(RuntimeError):
    """Raised when a replayed effect previously failed."""


@dataclass(frozen=True)
class IdempotencyEffectResult:
    effect_status: str
    response_payload: dict[str, Any]
    replayed: bool
    error_message: str | None = None


def _load_effect(
    *,
    session: Any,
    thread_id: str,
    node_name: str,
    effect_key: str,
) -> RuntimeIdempotencyEffect | None:
    return (
        session.query(RuntimeIdempotencyEffect)
        .filter(RuntimeIdempotencyEffect.thread_id == thread_id)
        .filter(RuntimeIdempotencyEffect.node_name == node_name)
        .filter(RuntimeIdempotencyEffect.effect_key == effect_key)
        .one_or_none()
    )


def execute_idempotent_effect(
    *,
    run_id: str,
    thread_id: str,
    node_name: str,
    effect_key: str,
    request_payload: dict[str, Any],
    effect_fn: Callable[[], dict[str, Any]],
) -> IdempotencyEffectResult:
    with SessionLocal() as session:
        resolve_thread_identity(session=session, run_id=run_id, thread_id=thread_id)
        existing_effect = _load_effect(
            session=session,
            thread_id=thread_id,
            node_name=node_name,
            effect_key=effect_key,
        )
        if existing_effect is not None:
            session.commit()
            if existing_effect.effect_status == "completed":
                return IdempotencyEffectResult(
                    effect_status=existing_effect.effect_status,
                    response_payload=dict(existing_effect.response_payload or {}),
                    replayed=True,
                    error_message=existing_effect.error_message,
                )
            if existing_effect.effect_status == "failed":
                raise IdempotencyReplayError(existing_effect.error_message or "Recorded effect previously failed.")
            effect_record = existing_effect
        else:
            effect_record = RuntimeIdempotencyEffect(
                run_id=run_id,
                thread_id=thread_id,
                node_name=node_name,
                effect_key=effect_key,
                effect_status="pending",
                request_payload=request_payload,
            )
            session.add(effect_record)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                recorded_effect = _load_effect(
                    session=session,
                    thread_id=thread_id,
                    node_name=node_name,
                    effect_key=effect_key,
                )
                if recorded_effect is None:
                    raise
                if recorded_effect.effect_status == "completed":
                    return IdempotencyEffectResult(
                        effect_status=recorded_effect.effect_status,
                        response_payload=dict(recorded_effect.response_payload or {}),
                        replayed=True,
                        error_message=recorded_effect.error_message,
                    )
                if recorded_effect.effect_status == "failed":
                    raise IdempotencyReplayError(
                        recorded_effect.error_message or "Recorded effect previously failed."
                    )
                effect_record = recorded_effect

        try:
            response_payload = effect_fn()
        except Exception as exc:
            effect_record.run_id = run_id
            effect_record.request_payload = request_payload
            effect_record.effect_status = "failed"
            effect_record.error_message = str(exc)
            session.add(effect_record)
            session.commit()
            raise

        effect_record.run_id = run_id
        effect_record.request_payload = request_payload
        effect_record.effect_status = "completed"
        effect_record.response_payload = response_payload
        effect_record.error_message = None
        session.add(effect_record)
        session.commit()
        return IdempotencyEffectResult(
            effect_status=effect_record.effect_status,
            response_payload=response_payload,
            replayed=False,
        )


__all__ = [
    "IdempotencyEffectResult",
    "IdempotencyReplayError",
    "execute_idempotent_effect",
]
