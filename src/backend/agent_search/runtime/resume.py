from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from langgraph.types import Command
from schemas import RuntimeQueryExpansionResumeEnvelope, RuntimeSubquestionResumeEnvelope


class ResumeTransitionError(ValueError):
    """Raised when a run is resumed from an invalid lifecycle state."""


_RESUMABLE_STATUSES = frozenset({"paused"})


def build_resume_command(resume: Any = True) -> Command:
    return Command(resume=resume)


def normalize_resume_payload(
    resume: Any = True,
    *,
    checkpoint_id: str | None = None,
) -> Any:
    if not isinstance(resume, (RuntimeSubquestionResumeEnvelope, RuntimeQueryExpansionResumeEnvelope)):
        return resume
    if checkpoint_id and resume.checkpoint_id != checkpoint_id:
        raise ResumeTransitionError(
            f"Resume checkpoint_id '{resume.checkpoint_id}' does not match paused checkpoint '{checkpoint_id}'."
        )
    return resume


def attach_checkpoint_metadata(interrupt_payload: Any, *, checkpoint_id: str | None = None) -> Any:
    if not isinstance(interrupt_payload, Mapping):
        return interrupt_payload
    normalized_payload = dict(interrupt_payload)
    if checkpoint_id and not normalized_payload.get("checkpoint_id"):
        normalized_payload["checkpoint_id"] = checkpoint_id
    return normalized_payload


def apply_subquestion_resume_decisions(
    subquestions: Sequence[str],
    *,
    resume: Any = True,
    interrupt_payload: Any | None = None,
) -> list[str]:
    baseline_subquestions = [str(subquestion) for subquestion in subquestions]
    if not isinstance(resume, RuntimeSubquestionResumeEnvelope):
        return baseline_subquestions

    checkpoint_id = None
    if isinstance(interrupt_payload, Mapping):
        raw_checkpoint_id = interrupt_payload.get("checkpoint_id")
        if raw_checkpoint_id is not None:
            checkpoint_id = str(raw_checkpoint_id)
    normalize_resume_payload(resume, checkpoint_id=checkpoint_id)

    indexed_items: list[tuple[int, str, str]] = []
    if isinstance(interrupt_payload, Mapping):
        raw_items = interrupt_payload.get("subquestions")
        if isinstance(raw_items, Sequence) and not isinstance(raw_items, (str, bytes, bytearray)):
            for fallback_index, raw_item in enumerate(raw_items):
                if not isinstance(raw_item, Mapping):
                    continue
                raw_id = raw_item.get("subquestion_id")
                if raw_id is None:
                    continue
                raw_index = raw_item.get("index", fallback_index)
                try:
                    item_index = int(raw_index)
                except (TypeError, ValueError):
                    item_index = fallback_index
                item_text = str(raw_item.get("sub_question", ""))
                indexed_items.append((item_index, str(raw_id), item_text))
    if not indexed_items:
        indexed_items = [
            (index, f"sq-{index + 1}", subquestion)
            for index, subquestion in enumerate(baseline_subquestions)
        ]

    indexed_items.sort(key=lambda item: item[0])
    available_items = {subquestion_id: (index, text) for index, subquestion_id, text in indexed_items}
    if len(available_items) != len(indexed_items):
        raise ResumeTransitionError("Resume decisions contain duplicate subquestion identifiers in interrupt payload.")

    decisions_by_id: dict[str, Any] = {}
    for decision in resume.decisions:
        if decision.subquestion_id in decisions_by_id:
            raise ResumeTransitionError(f"Duplicate resume decision for subquestion_id '{decision.subquestion_id}'.")
        if decision.subquestion_id not in available_items:
            raise ResumeTransitionError(f"Unknown subquestion_id '{decision.subquestion_id}' for paused checkpoint.")
        decisions_by_id[decision.subquestion_id] = decision

    resolved_subquestions: list[str] = []
    for subquestion_id, (index, fallback_text) in available_items.items():
        current_text = baseline_subquestions[index] if 0 <= index < len(baseline_subquestions) else fallback_text
        decision = decisions_by_id.get(subquestion_id)
        if decision is None or decision.action in {"approve", "skip"}:
            resolved_subquestions.append(current_text)
            continue
        if decision.action == "edit":
            resolved_subquestions.append((decision.edited_text or "").strip())
            continue
        if decision.action == "deny":
            continue
        raise ResumeTransitionError(f"Unsupported resume action '{decision.action}'.")
    return resolved_subquestions


def apply_query_expansion_resume_decisions(
    expanded_queries: Sequence[str],
    *,
    resume: Any = True,
    interrupt_payload: Any | None = None,
) -> list[str]:
    baseline_queries = [str(query).strip() for query in expanded_queries if str(query).strip()]
    if not isinstance(resume, RuntimeQueryExpansionResumeEnvelope):
        return baseline_queries

    checkpoint_id = None
    indexed_items: list[tuple[int, str, str]] = []
    if isinstance(interrupt_payload, Mapping):
        raw_checkpoint_id = interrupt_payload.get("checkpoint_id")
        if raw_checkpoint_id is not None:
            checkpoint_id = str(raw_checkpoint_id)
        raw_items = interrupt_payload.get("expansions")
        if isinstance(raw_items, Sequence) and not isinstance(raw_items, (str, bytes, bytearray)):
            for fallback_index, raw_item in enumerate(raw_items):
                if not isinstance(raw_item, Mapping):
                    continue
                raw_id = raw_item.get("expansion_id")
                if raw_id is None:
                    continue
                raw_index = raw_item.get("index", fallback_index)
                try:
                    item_index = int(raw_index)
                except (TypeError, ValueError):
                    item_index = fallback_index
                item_text = str(raw_item.get("query", "")).strip()
                indexed_items.append((item_index, str(raw_id), item_text))
    normalize_resume_payload(resume, checkpoint_id=checkpoint_id)

    if not indexed_items:
        indexed_items = [
            (index, f"qe-{index + 1}", query)
            for index, query in enumerate(baseline_queries)
        ]

    indexed_items.sort(key=lambda item: item[0])
    available_items = {expansion_id: (index, text) for index, expansion_id, text in indexed_items}
    if len(available_items) != len(indexed_items):
        raise ResumeTransitionError("Resume decisions contain duplicate expansion identifiers in interrupt payload.")

    decisions_by_id: dict[str, Any] = {}
    for decision in resume.decisions:
        if decision.expansion_id in decisions_by_id:
            raise ResumeTransitionError(f"Duplicate resume decision for expansion_id '{decision.expansion_id}'.")
        if decision.expansion_id not in available_items:
            raise ResumeTransitionError(f"Unknown expansion_id '{decision.expansion_id}' for paused checkpoint.")
        decisions_by_id[decision.expansion_id] = decision

    resolved_queries: list[str] = []
    seen_queries: set[str] = set()
    for expansion_id, (index, fallback_text) in available_items.items():
        current_query = baseline_queries[index] if 0 <= index < len(baseline_queries) else fallback_text
        decision = decisions_by_id.get(expansion_id)
        if decision is None or decision.action in {"approve", "skip"}:
            next_query = current_query
        elif decision.action == "edit":
            next_query = (decision.edited_query or "").strip()
        elif decision.action == "deny":
            continue
        else:
            raise ResumeTransitionError(f"Unsupported resume action '{decision.action}'.")

        if not next_query:
            continue
        lowered = next_query.casefold()
        if lowered in seen_queries:
            continue
        seen_queries.add(lowered)
        resolved_queries.append(next_query)
    return resolved_queries


def ensure_resume_allowed(status: str) -> None:
    normalized_status = status.strip().lower()
    if normalized_status in _RESUMABLE_STATUSES:
        return
    raise ResumeTransitionError(f"Run cannot be resumed from status '{status}'.")


__all__ = [
    "ResumeTransitionError",
    "apply_query_expansion_resume_decisions",
    "apply_subquestion_resume_decisions",
    "attach_checkpoint_metadata",
    "build_resume_command",
    "ensure_resume_allowed",
    "normalize_resume_payload",
]
