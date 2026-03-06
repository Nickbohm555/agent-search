import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schemas import SubQuestionAnswer
from services.refinement_decision_service import should_refine


def test_should_refine_true_when_initial_answer_reports_no_relevant_docs() -> None:
    decision = should_refine(
        question="What changed in policy X?",
        initial_answer="No relevant docs were found to answer this question.",
        sub_qa=[
            SubQuestionAnswer(
                sub_question="What changed?",
                sub_answer="No relevant evidence found.",
                answerable=False,
                verification_reason="subanswer_reports_insufficient_evidence",
            )
        ],
    )

    assert decision.refinement_needed is True
    assert decision.reason == "initial_answer_reports_insufficient_evidence"


def test_should_refine_false_when_answer_is_supported() -> None:
    decision = should_refine(
        question="What changed in policy X?",
        initial_answer="Policy X changed in 2025 and clarified compliance deadlines.",
        sub_qa=[
            SubQuestionAnswer(
                sub_question="What changed in policy X?",
                sub_answer="Policy X changed in 2025.",
                answerable=True,
                verification_reason="grounded_in_reranked_documents",
            ),
            SubQuestionAnswer(
                sub_question="What compliance rules changed?",
                sub_answer="Deadlines were clarified in 2025.",
                answerable=True,
                verification_reason="grounded_in_reranked_documents",
            ),
        ],
    )

    assert decision.refinement_needed is False
    assert decision.reason.startswith("sufficient_answerable_ratio:")


def test_should_refine_true_when_initial_answer_reports_no_information_available() -> None:
    decision = should_refine(
        question="What happened in policy XZQ-999?",
        initial_answer="There is no information available about policy XZQ-999 in the provided evidence.",
        sub_qa=[
            SubQuestionAnswer(
                sub_question="policy XZQ-999?",
                sub_answer="No information available.",
                answerable=True,
                verification_reason="grounded_in_reranked_documents",
            )
        ],
    )

    assert decision.refinement_needed is True
    assert decision.reason == "initial_answer_reports_insufficient_evidence"
