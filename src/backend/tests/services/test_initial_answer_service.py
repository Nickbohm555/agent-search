import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schemas import SubQuestionAnswer
from services import initial_answer_service


def test_generate_initial_answer_fallback_prefers_answerable_subanswers(monkeypatch) -> None:
    monkeypatch.setattr(initial_answer_service, "_OPENAI_API_KEY", "")

    sub_qa = [
        SubQuestionAnswer(
            sub_question="What changed in NATO policy?",
            sub_answer="NATO updated force posture in 2025 [1] (source: wiki://nato).",
            answerable=True,
            verification_reason="grounded_in_reranked_documents",
        ),
        SubQuestionAnswer(
            sub_question="What did member states commit to?",
            sub_answer="Members committed to increased readiness (source: wiki://readiness).",
            answerable=True,
            verification_reason="grounded_in_reranked_documents",
        ),
    ]

    output = initial_answer_service.generate_initial_answer(
        main_question="What changed in NATO policy?",
        initial_search_context=[
            {
                "title": "NATO communique",
                "source": "wiki://nato-communique",
                "snippet": "Communique summary.",
            }
        ],
        sub_qa=sub_qa,
    )

    assert output
    assert "NATO updated force posture in 2025" in output
    assert "[1]" in output


def test_generate_initial_answer_fallback_uses_initial_context_when_no_subanswers(monkeypatch) -> None:
    monkeypatch.setattr(initial_answer_service, "_OPENAI_API_KEY", "")

    output = initial_answer_service.generate_initial_answer(
        main_question="What changed in policy?",
        initial_search_context=[
            {
                "title": "Policy update",
                "source": "wiki://policy",
                "snippet": "Policy guidance changed in 2025.",
            }
        ],
        sub_qa=[],
    )

    assert output
    assert "Policy guidance changed in 2025" in output
    assert "source: wiki://policy" in output


def test_generate_initial_answer_prompt_preserves_citation_instructions(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class _FakeResponse:
        content = "Final answer [1] (source: wiki://nato)."

    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            captured["model"] = model
            captured["temperature"] = str(temperature)

        def invoke(self, prompt: str) -> _FakeResponse:
            captured["prompt"] = prompt
            return _FakeResponse()

    monkeypatch.setattr(initial_answer_service, "_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(initial_answer_service, "ChatOpenAI", _FakeChatOpenAI)

    output = initial_answer_service.generate_initial_answer(
        main_question="What changed in NATO policy?",
        initial_search_context=[
            {
                "title": "NATO communique",
                "source": "wiki://nato-communique",
                "snippet": "Communique summary.",
            }
        ],
        sub_qa=[
            SubQuestionAnswer(
                sub_question="What changed in NATO policy?",
                sub_answer="NATO updated force posture [1] (source: wiki://nato).",
                answerable=True,
                verification_reason="grounded_in_reranked_documents",
            )
        ],
    )

    assert output == "Final answer [1] (source: wiki://nato)."
    assert "Preserve citation markers from sub-question answers exactly" in captured["prompt"]
    assert "Do not collapse cited evidence into an uncited summary." in captured["prompt"]
