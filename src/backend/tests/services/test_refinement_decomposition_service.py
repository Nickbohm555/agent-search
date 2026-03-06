import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schemas import SubQuestionAnswer
from services.refinement_decomposition_service import (
    _sanitize_refined_subquestions,
    refine_subquestions,
)


def test_sanitize_refined_subquestions_dedupes_and_excludes_existing() -> None:
    output = _sanitize_refined_subquestions(
        candidates=[
            "What changed in policy X?",
            "What Changed in Policy X",
            "Which primary source confirms policy X changes",
            "Which primary source confirms policy X changes?",
        ],
        existing_subquestions=["What changed in policy X?"],
    )

    assert output == ["Which primary source confirms policy X changes?"]


def test_refine_subquestions_fallback_targets_unanswerable_gaps(monkeypatch) -> None:
    monkeypatch.setattr("services.refinement_decomposition_service._OPENAI_API_KEY", "")

    sub_qa = [
        SubQuestionAnswer(
            sub_question="What changed in policy X?",
            sub_answer="No relevant evidence found.",
            answerable=False,
            verification_reason="subanswer_reports_insufficient_evidence",
        )
    ]
    output = refine_subquestions(
        question="What changed in policy X?",
        initial_answer="Initial answer still lacks support.",
        sub_qa=sub_qa,
    )

    assert output
    assert all(item.endswith("?") for item in output)
    assert "What changed in policy X?" not in output
