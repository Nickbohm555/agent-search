from __future__ import annotations

from typing import Any

from langgraph.types import Command


class ResumeTransitionError(ValueError):
    """Raised when a run is resumed from an invalid lifecycle state."""


_RESUMABLE_STATUSES = frozenset({"paused"})


def build_resume_command(resume: Any = True) -> Command:
    return Command(resume=resume)


def ensure_resume_allowed(status: str) -> None:
    normalized_status = status.strip().lower()
    if normalized_status in _RESUMABLE_STATUSES:
        return
    raise ResumeTransitionError(f"Run cannot be resumed from status '{status}'.")


__all__ = [
    "ResumeTransitionError",
    "build_resume_command",
    "ensure_resume_allowed",
]
