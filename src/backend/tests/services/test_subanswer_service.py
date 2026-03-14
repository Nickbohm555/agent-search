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
    captured: dict[str, str] = {}

    class _FakeResponse:
        content = "Policy changed in 2025 [1]."

    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            assert model
            assert temperature == subanswer_service._SUBANSWER_TEMPERATURE

        def invoke(self, prompt: str, config=None):
            captured["prompt"] = prompt
            assert "Sub-question:" in prompt
            assert "Reranked evidence:" in prompt
            return _FakeResponse()

    monkeypatch.setattr(subanswer_service, "ChatOpenAI", _FakeChatOpenAI)

    output = subanswer_service.generate_subanswer(
        sub_question="What changed in NATO policy?",
        reranked_retrieved_output="1. title=NATO Policy source=wiki://nato content=Policy changed in 2025.",
    )

    assert output == "Policy changed in 2025 [1]."
    assert "cite claims with [index]" in captured["prompt"]


def test_generate_subanswer_uses_custom_prompt_template(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class _FakeResponse:
        content = "Custom answer [1]."

    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            assert model
            assert temperature == subanswer_service._SUBANSWER_TEMPERATURE

        def invoke(self, prompt: str, config=None):
            captured["prompt"] = prompt
            return _FakeResponse()

    monkeypatch.setattr(subanswer_service, "ChatOpenAI", _FakeChatOpenAI)

    output = subanswer_service.generate_subanswer(
        sub_question="What changed in NATO policy?",
        reranked_retrieved_output="1. title=NATO Policy source=wiki://nato content=Policy changed in 2025.",
        prompt_template="Q={sub_question}\nCTX={context_block}",
    )

    assert output == "Custom answer [1]."
    assert captured["prompt"] == (
        "Q=What changed in NATO policy?\n"
        "CTX=[1] title=NATO Policy source=wiki://nato content=Policy changed in 2025."
    )


def test_generate_subanswer_fallback_ignores_prompt_override_without_docs() -> None:
    output = subanswer_service.generate_subanswer(
        sub_question="What changed in NATO policy?",
        reranked_retrieved_output="Non-parseable retrieval output",
        prompt_template="unused {sub_question} {context_block}",
    )

    assert output == "No relevant evidence found in reranked documents."


def test_generate_subanswer_prompt_includes_full_ranked_document_list(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class _FakeResponse:
        content = "Answer [4]."

    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            assert model
            assert temperature == subanswer_service._SUBANSWER_TEMPERATURE

        def invoke(self, prompt: str, config=None):
            captured["prompt"] = prompt
            return _FakeResponse()

    monkeypatch.setattr(subanswer_service, "ChatOpenAI", _FakeChatOpenAI)

    output = subanswer_service.generate_subanswer(
        sub_question="What happened most recently?",
        reranked_retrieved_output=(
            "1. title=Doc 1 source=wiki://doc1 content=One.\n"
            "2. title=Doc 2 source=wiki://doc2 content=Two.\n"
            "3. title=Doc 3 source=wiki://doc3 content=Three.\n"
            "4. title=Doc 4 source=wiki://doc4 content=Four."
        ),
    )

    assert output == "Answer [4]."
    assert "[1] title=Doc 1 source=wiki://doc1 content=One." in captured["prompt"]
    assert "[4] title=Doc 4 source=wiki://doc4 content=Four." in captured["prompt"]


def test_generate_subanswer_default_prompt_matches_constant(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class _FakeResponse:
        content = "Answer [1]."

    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            assert model
            assert temperature == subanswer_service._SUBANSWER_TEMPERATURE

        def invoke(self, prompt: str, config=None):
            captured["prompt"] = prompt
            return _FakeResponse()

    monkeypatch.setattr(subanswer_service, "ChatOpenAI", _FakeChatOpenAI)

    sub_question = "What changed in NATO policy?"
    reranked_output = "1. title=NATO Policy source=wiki://nato content=Policy changed in 2025."
    output = subanswer_service.generate_subanswer(
        sub_question=sub_question,
        reranked_retrieved_output=reranked_output,
    )

    assert output == "Answer [1]."
    assert captured["prompt"] == subanswer_service.DEFAULT_SUBANSWER_PROMPT_TEMPLATE.format(
        sub_question=sub_question,
        context_block="[1] title=NATO Policy source=wiki://nato content=Policy changed in 2025.",
    )


def test_generate_subanswer_unset_prompt_matches_explicit_default_template(monkeypatch) -> None:
    captured_prompts: list[str] = []

    class _FakeResponse:
        content = "Answer [1]."

    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            assert model
            assert temperature == subanswer_service._SUBANSWER_TEMPERATURE

        def invoke(self, prompt: str, config=None):
            captured_prompts.append(prompt)
            return _FakeResponse()

    monkeypatch.setattr(subanswer_service, "_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(subanswer_service, "ChatOpenAI", _FakeChatOpenAI)

    call_kwargs = {
        "sub_question": "What changed in NATO policy?",
        "reranked_retrieved_output": (
            "1. title=NATO Policy source=wiki://nato content=Policy changed in 2025."
        ),
    }

    unset_output = subanswer_service.generate_subanswer(**call_kwargs)
    default_output = subanswer_service.generate_subanswer(
        **call_kwargs,
        prompt_template=subanswer_service.DEFAULT_SUBANSWER_PROMPT_TEMPLATE,
    )

    assert unset_output == "Answer [1]."
    assert default_output == "Answer [1]."
    assert captured_prompts == [
        subanswer_service.DEFAULT_SUBANSWER_PROMPT_TEMPLATE.format(
            sub_question="What changed in NATO policy?",
            context_block="[1] title=NATO Policy source=wiki://nato content=Policy changed in 2025.",
        ),
        subanswer_service.DEFAULT_SUBANSWER_PROMPT_TEMPLATE.format(
            sub_question="What changed in NATO policy?",
            context_block="[1] title=NATO Policy source=wiki://nato content=Policy changed in 2025.",
        ),
    ]


def test_generate_subanswer_fallback_stays_stable_when_prompt_override_llm_fails(monkeypatch) -> None:
    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            assert model
            assert temperature == subanswer_service._SUBANSWER_TEMPERATURE

        def invoke(self, prompt: str, config=None):
            raise RuntimeError("llm unavailable")

    monkeypatch.setattr(subanswer_service, "_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(subanswer_service, "ChatOpenAI", _FakeChatOpenAI)

    output = subanswer_service.generate_subanswer(
        sub_question="What changed in NATO policy?",
        reranked_retrieved_output="1. title=NATO Policy source=wiki://nato content=Policy changed in 2025.",
        prompt_template="Q={sub_question}\nCTX={context_block}",
    )

    assert output == "Policy changed in 2025. (source: wiki://nato)"
