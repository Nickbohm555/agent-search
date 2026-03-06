import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services import subanswer_service


def test_generate_subanswer_returns_fallback_when_no_parseable_docs() -> None:
    output = subanswer_service.generate_subanswer(
        sub_question="What changed in NATO policy?",
        reranked_retrieved_output="Non-parseable retrieval output",
    )

    assert output == "No relevant evidence found in reranked documents."


def test_generate_subanswer_uses_llm_when_available(monkeypatch) -> None:
    class _FakeResponse:
        content = "Policy changed in 2025 (source: wiki://nato)."

    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            assert model
            assert temperature == subanswer_service._SUBANSWER_TEMPERATURE

        def invoke(self, prompt: str):
            assert "Sub-question:" in prompt
            assert "Reranked evidence:" in prompt
            return _FakeResponse()

    monkeypatch.setattr(subanswer_service, "ChatOpenAI", _FakeChatOpenAI)

    output = subanswer_service.generate_subanswer(
        sub_question="What changed in NATO policy?",
        reranked_retrieved_output="1. title=NATO Policy source=wiki://nato content=Policy changed in 2025.",
    )

    assert output == "Policy changed in 2025 (source: wiki://nato)."
