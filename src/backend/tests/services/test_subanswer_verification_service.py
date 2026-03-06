import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.subanswer_verification_service import verify_subanswer


def test_verify_subanswer_returns_false_when_subanswer_reports_insufficient_evidence() -> None:
    result = verify_subanswer(
        sub_question="What changed in policy X?",
        sub_answer="There is insufficient evidence to answer this question.",
        reranked_retrieved_output="1. title=Policy X source=wiki://policy-x content=Policy X changed in 2025.",
    )

    assert result.answerable is False
    assert result.reason == "subanswer_reports_insufficient_evidence"


def test_verify_subanswer_returns_false_when_not_grounded_in_docs() -> None:
    result = verify_subanswer(
        sub_question="What changed in policy X?",
        sub_answer="It changed in 1999 according to unrelated records.",
        reranked_retrieved_output="1. title=Policy X source=wiki://policy-x content=Policy X changed in 2025.",
    )

    assert result.answerable is False
    assert result.reason == "insufficient_evidence_overlap"


def test_verify_subanswer_returns_true_when_grounded_in_docs() -> None:
    result = verify_subanswer(
        sub_question="What changed in policy X?",
        sub_answer="Policy X changed in 2025 and adjusted compliance rules.",
        reranked_retrieved_output="1. title=Policy X source=wiki://policy-x content=Policy X changed in 2025 with updated compliance rules.",
    )

    assert result.answerable is True
    assert result.reason == "grounded_in_reranked_documents"
