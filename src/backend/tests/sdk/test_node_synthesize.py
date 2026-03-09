from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime.nodes import synthesize
from schemas import CitationSourceRow, GraphRunMetadata, SubQuestionAnswer, SubQuestionArtifacts, SynthesizeFinalNodeInput


def _node_input(
    *,
    sub_qa: list[SubQuestionAnswer] | None = None,
    sub_question_artifacts: list[SubQuestionArtifacts] | None = None,
) -> SynthesizeFinalNodeInput:
    return SynthesizeFinalNodeInput(
        main_question="Explain VAT policy changes.",
        sub_qa=sub_qa or [],
        sub_question_artifacts=sub_question_artifacts or [],
        run_metadata=GraphRunMetadata(
            run_id="run-node-synthesize",
            trace_id="trace-node-synthesize",
            correlation_id="corr-node-synthesize",
        ),
    )


def test_run_synthesize_node_returns_generated_answer_when_citations_are_valid() -> None:
    captured: dict[str, object] = {}

    def _fake_generate_final_synthesis_answer(*, main_question: str, sub_qa, callbacks=None):
        captured["main_question"] = main_question
        captured["sub_qa_count"] = len(sub_qa)
        captured["callbacks"] = callbacks
        return "Final synthesis [1] (source: wiki://vat-policy)."

    callback_marker = object()
    output = synthesize.run_synthesize_node(
        node_input=_node_input(
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="What changed in VAT policy?",
                    sub_answer="VAT changed in 2025 [1] (source: wiki://vat-policy).",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                )
            ],
            sub_question_artifacts=[
                SubQuestionArtifacts(
                    sub_question="What changed in VAT policy?",
                    citation_rows_by_index={
                        1: CitationSourceRow(
                            citation_index=1,
                            rank=1,
                            title="VAT policy",
                            source="wiki://vat-policy",
                            content="VAT changed in 2025.",
                            document_id="doc-1",
                        )
                    },
                )
            ],
        ),
        callbacks=[callback_marker],
        generate_final_synthesis_answer_fn=_fake_generate_final_synthesis_answer,
    )

    assert output.final_answer == "Final synthesis [1] (source: wiki://vat-policy)."
    assert captured["main_question"] == "Explain VAT policy changes."
    assert captured["sub_qa_count"] == 1
    assert captured["callbacks"] == [callback_marker]


def test_run_synthesize_node_falls_back_to_answerable_subanswers_on_missing_citations() -> None:
    output = synthesize.run_synthesize_node(
        node_input=_node_input(
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="What changed in VAT policy?",
                    sub_answer="VAT changed in 2025 [1] (source: wiki://vat-policy).",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                ),
                SubQuestionAnswer(
                    sub_question="What changed regionally?",
                    sub_answer="Regional note [2] (source: wiki://regional-note).",
                    answerable=False,
                    verification_reason="unsupported",
                ),
            ],
            sub_question_artifacts=[
                SubQuestionArtifacts(
                    sub_question="What changed in VAT policy?",
                    citation_rows_by_index={
                        1: CitationSourceRow(
                            citation_index=1,
                            rank=1,
                            title="VAT policy",
                            source="wiki://vat-policy",
                            content="VAT changed in 2025.",
                            document_id="doc-1",
                        )
                    },
                )
            ],
        ),
        generate_final_synthesis_answer_fn=lambda **_kwargs: "VAT policy changed in 2025.",
    )

    assert output.final_answer == "VAT changed in 2025 [1] (source: wiki://vat-policy)."


def test_run_synthesize_node_falls_back_on_invalid_citation_indices() -> None:
    output = synthesize.run_synthesize_node(
        node_input=_node_input(
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="What changed in VAT policy?",
                    sub_answer="VAT changed in 2025 [1] (source: wiki://vat-policy).",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                )
            ],
            sub_question_artifacts=[
                SubQuestionArtifacts(
                    sub_question="What changed in VAT policy?",
                    citation_rows_by_index={
                        1: CitationSourceRow(
                            citation_index=1,
                            rank=1,
                            title="VAT policy",
                            source="wiki://vat-policy",
                            content="VAT changed in 2025.",
                            document_id="doc-1",
                        )
                    },
                )
            ],
        ),
        generate_final_synthesis_answer_fn=lambda **_kwargs: "VAT policy changed in 2025 [9].",
    )

    assert output.final_answer == "VAT changed in 2025 [1] (source: wiki://vat-policy)."


def test_run_synthesize_node_uses_timeout_prefix_when_no_citable_fallback_exists() -> None:
    output = synthesize.run_synthesize_node(
        node_input=_node_input(
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="What changed in VAT policy?",
                    sub_answer="VAT changed in 2025.",
                    answerable=False,
                    verification_reason="unsupported",
                )
            ]
        ),
        generate_final_synthesis_answer_fn=lambda **_kwargs: "",
    )

    assert output.final_answer == "Answer generation timed out; partial context only. VAT changed in 2025."
