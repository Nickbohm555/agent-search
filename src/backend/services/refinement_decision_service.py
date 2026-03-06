from __future__ import annotations

import os
from dataclasses import dataclass

from schemas import SubQuestionAnswer

_INSUFFICIENT_ANSWER_PATTERNS = (
    "no relevant docs",
    "no relevant evidence",
    "insufficient evidence",
    "not enough evidence",
    "cannot determine",
    "unable to determine",
    "insufficient information",
)
_MIN_ANSWERABLE_RATIO = float(os.getenv("REFINEMENT_MIN_ANSWERABLE_RATIO", "0.5"))


@dataclass(frozen=True)
class RefinementDecision:
    refinement_needed: bool
    reason: str


def should_refine(
    *,
    question: str,
    initial_answer: str,
    sub_qa: list[SubQuestionAnswer],
) -> RefinementDecision:
    _ = question  # Reserved for later, richer question-to-answer coverage checks.

    normalized_answer = (initial_answer or "").strip()
    if not normalized_answer:
        return RefinementDecision(refinement_needed=True, reason="initial_answer_empty")

    lowered_answer = normalized_answer.lower()
    for pattern in _INSUFFICIENT_ANSWER_PATTERNS:
        if pattern in lowered_answer:
            return RefinementDecision(
                refinement_needed=True,
                reason="initial_answer_reports_insufficient_evidence",
            )

    if not sub_qa:
        return RefinementDecision(refinement_needed=True, reason="no_subquestion_answers")

    answerable_count = sum(1 for item in sub_qa if item.answerable)
    if answerable_count == 0:
        return RefinementDecision(refinement_needed=True, reason="no_answerable_subanswers")

    answerable_ratio = answerable_count / len(sub_qa)
    if answerable_ratio < _MIN_ANSWERABLE_RATIO:
        return RefinementDecision(
            refinement_needed=True,
            reason=f"low_answerable_ratio:{answerable_ratio:.2f}",
        )

    return RefinementDecision(
        refinement_needed=False,
        reason=f"sufficient_answerable_ratio:{answerable_ratio:.2f}",
    )
