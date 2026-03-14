from __future__ import annotations

from types import SimpleNamespace

from services import initial_answer_service, subanswer_service
from schemas import SubQuestionAnswer


def test_subanswer_prompt_customization_only_overrides_instruction_block(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeChatOpenAI:
        def __init__(self, *args, **kwargs):
            captured["init"] = {"args": args, "kwargs": kwargs}

        def invoke(self, prompt, config=None):
            captured["prompt"] = prompt
            captured["config"] = config
            return SimpleNamespace(content="Grounded answer [1]")

    monkeypatch.setattr(subanswer_service, "_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(subanswer_service, "ChatOpenAI", _FakeChatOpenAI)

    output = subanswer_service.generate_subanswer(
        sub_question="What changed in policy X?",
        reranked_retrieved_output="1. title=Policy X source=wiki://policy-x content=Policy X changed in 2025.",
        prompt_template="Custom instructions with literal {sub_question}.",
    )

    assert output == "Grounded answer [1]"
    assert captured["prompt"] == (
        "Custom instructions with literal {sub_question}.\n\n"
        "Sub-question:\nWhat changed in policy X?\n\n"
        "Reranked evidence:\n[1] title=Policy X source=wiki://policy-x content=Policy X changed in 2025.\n"
    )


def test_synthesis_prompt_customization_only_overrides_instruction_block(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeChatOpenAI:
        def __init__(self, *args, **kwargs):
            captured["init"] = {"args": args, "kwargs": kwargs}

        def invoke(self, prompt, config=None):
            captured["prompt"] = prompt
            captured["config"] = config
            return SimpleNamespace(content="Synthesized answer [1]")

    monkeypatch.setattr(initial_answer_service, "_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(initial_answer_service, "ChatOpenAI", _FakeChatOpenAI)

    output = initial_answer_service.generate_final_synthesis_answer(
        main_question="What is the final answer?",
        sub_qa=[
            SubQuestionAnswer(
                sub_question="What changed in policy X?",
                sub_answer="Policy X changed in 2025. [1]",
                answerable=True,
                verification_reason="grounded_in_reranked_documents",
            )
        ],
        prompt_template="Custom synthesis instructions with literal {main_question}.",
    )

    assert output == "Synthesized answer [1]"
    assert captured["prompt"] == (
        "Custom synthesis instructions with literal {main_question}.\n\n"
        "Main question:\nWhat is the final answer?\n\n"
        "Initial retrieval context:\nNone\n\n"
        "Sub-question answers:\n[1] sub_question=What changed in policy X?\n"
        "answerable=True\n"
        "verification_reason=grounded_in_reranked_documents\n"
        "sub_answer=Policy X changed in 2025. [1]\n"
    )
