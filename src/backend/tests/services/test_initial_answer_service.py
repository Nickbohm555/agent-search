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

        def invoke(self, prompt: str, config=None) -> _FakeResponse:
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


def test_generate_initial_answer_uses_custom_prompt_template(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class _FakeResponse:
        content = "Custom synthesis [1] (source: wiki://nato)."

    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            captured["model"] = model
            captured["temperature"] = str(temperature)

        def invoke(self, prompt: str, config=None) -> _FakeResponse:
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
        prompt_template=(
            "MAIN={main_question}\n"
            "CTX={initial_context}\n"
            "SUBS={sub_qa_context}"
        ),
    )

    assert output == "Custom synthesis [1] (source: wiki://nato)."
    assert captured["prompt"] == (
        "MAIN=What changed in NATO policy?\n"
        "CTX=[1] title=NATO communique source=wiki://nato-communique snippet=Communique summary.\n"
        "SUBS=[1] sub_question=What changed in NATO policy?\n"
        "answerable=True\n"
        "verification_reason=grounded_in_reranked_documents\n"
        "sub_answer=NATO updated force posture [1] (source: wiki://nato)."
    )


def test_generate_initial_answer_fallback_ignores_prompt_override_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(initial_answer_service, "_OPENAI_API_KEY", "")

    output = initial_answer_service.generate_initial_answer(
        main_question="What changed in NATO policy?",
        initial_search_context=[],
        sub_qa=[
            SubQuestionAnswer(
                sub_question="What changed in NATO policy?",
                sub_answer="NATO updated force posture [1] (source: wiki://nato).",
                answerable=True,
                verification_reason="grounded_in_reranked_documents",
            )
        ],
        prompt_template="unused {main_question} {initial_context} {sub_qa_context}",
    )

    assert output == "NATO updated force posture [1] (source: wiki://nato)."


def test_generate_initial_answer_unset_prompt_matches_explicit_default_template(monkeypatch) -> None:
    captured_prompts: list[str] = []

    class _FakeResponse:
        content = "Final answer [1] (source: wiki://nato)."

    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            assert model
            assert temperature == initial_answer_service._INITIAL_ANSWER_TEMPERATURE

        def invoke(self, prompt: str, config=None) -> _FakeResponse:
            captured_prompts.append(prompt)
            return _FakeResponse()

    monkeypatch.setattr(initial_answer_service, "_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(initial_answer_service, "ChatOpenAI", _FakeChatOpenAI)

    initial_search_context = [
        {
            "title": "NATO communique",
            "source": "wiki://nato-communique",
            "snippet": "Communique summary.",
        }
    ]
    sub_qa = [
        SubQuestionAnswer(
            sub_question="What changed in NATO policy?",
            sub_answer="NATO updated force posture [1] (source: wiki://nato).",
            answerable=True,
            verification_reason="grounded_in_reranked_documents",
        )
    ]

    unset_output = initial_answer_service.generate_initial_answer(
        main_question="What changed in NATO policy?",
        initial_search_context=initial_search_context,
        sub_qa=sub_qa,
    )
    default_output = initial_answer_service.generate_initial_answer(
        main_question="What changed in NATO policy?",
        initial_search_context=initial_search_context,
        sub_qa=sub_qa,
        prompt_template=initial_answer_service.DEFAULT_INITIAL_ANSWER_PROMPT_TEMPLATE,
    )

    expected_prompt = initial_answer_service.DEFAULT_INITIAL_ANSWER_PROMPT_TEMPLATE.format(
        main_question="What changed in NATO policy?",
        initial_context="[1] title=NATO communique source=wiki://nato-communique snippet=Communique summary.",
        sub_qa_context=(
            "[1] sub_question=What changed in NATO policy?\n"
            "answerable=True\n"
            "verification_reason=grounded_in_reranked_documents\n"
            "sub_answer=NATO updated force posture [1] (source: wiki://nato)."
        ),
    )

    assert unset_output == "Final answer [1] (source: wiki://nato)."
    assert default_output == "Final answer [1] (source: wiki://nato)."
    assert captured_prompts == [expected_prompt, expected_prompt]


def test_generate_initial_answer_fallback_stays_stable_when_prompt_override_llm_fails(monkeypatch) -> None:
    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            assert model
            assert temperature == initial_answer_service._INITIAL_ANSWER_TEMPERATURE

        def invoke(self, prompt: str, config=None) -> str:
            raise RuntimeError("llm unavailable")

    monkeypatch.setattr(initial_answer_service, "_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(initial_answer_service, "ChatOpenAI", _FakeChatOpenAI)

    output = initial_answer_service.generate_initial_answer(
        main_question="What changed in NATO policy?",
        initial_search_context=[],
        sub_qa=[
            SubQuestionAnswer(
                sub_question="What changed in NATO policy?",
                sub_answer="NATO updated force posture [1] (source: wiki://nato).",
                answerable=True,
                verification_reason="grounded_in_reranked_documents",
            )
        ],
        prompt_template=(
            "MAIN={main_question}\n"
            "CTX={initial_context}\n"
            "SUBS={sub_qa_context}"
        ),
    )

    assert output == "NATO updated force posture [1] (source: wiki://nato)."


def test_generate_final_synthesis_answer_preserves_grounded_subanswer_citations(monkeypatch) -> None:
    monkeypatch.setattr(initial_answer_service, "_OPENAI_API_KEY", "")

    output = initial_answer_service.generate_final_synthesis_answer(
        main_question="What changed in NATO policy?",
        sub_qa=[
            SubQuestionAnswer(
                sub_question="What changed in NATO policy?",
                sub_answer="NATO updated force posture in 2025 [1] (source: wiki://nato).",
                answerable=True,
                verification_reason="grounded_in_reranked_documents",
            ),
            SubQuestionAnswer(
                sub_question="What did member states commit to?",
                sub_answer="Members committed to increased readiness [2] (source: wiki://readiness).",
                answerable=True,
                verification_reason="grounded_in_reranked_documents",
            ),
        ],
    )

    assert output
    assert "[1]" in output
    assert "source: wiki://nato" in output


def test_generate_final_synthesis_answer_passes_prompt_template(monkeypatch) -> None:
    captured: dict[str, str | list[SubQuestionAnswer] | None] = {}

    def _fake_generate_initial_answer(
        *,
        main_question: str,
        initial_search_context: list[dict[str, str]],
        sub_qa: list[SubQuestionAnswer],
        prompt_template: str | None = None,
        callbacks=None,
    ) -> str:
        captured["main_question"] = main_question
        captured["initial_search_context"] = initial_search_context
        captured["sub_qa"] = sub_qa
        captured["prompt_template"] = prompt_template
        captured["callbacks"] = callbacks
        return "Final answer [1] (source: wiki://nato)."

    monkeypatch.setattr(initial_answer_service, "generate_initial_answer", _fake_generate_initial_answer)

    sub_qa = [
        SubQuestionAnswer(
            sub_question="What changed in NATO policy?",
            sub_answer="NATO updated force posture [1] (source: wiki://nato).",
            answerable=True,
            verification_reason="grounded_in_reranked_documents",
        )
    ]
    output = initial_answer_service.generate_final_synthesis_answer(
        main_question="What changed in NATO policy?",
        sub_qa=sub_qa,
        prompt_template="custom-template",
    )

    assert output == "Final answer [1] (source: wiki://nato)."
    assert captured["main_question"] == "What changed in NATO policy?"
    assert captured["initial_search_context"] == []
    assert captured["sub_qa"] == sub_qa
    assert captured["prompt_template"] == "custom-template"
