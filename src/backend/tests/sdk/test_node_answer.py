from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime.nodes import answer
from schemas import AnswerSubquestionNodeInput, CitationSourceRow, GraphRunMetadata


def _node_input(
    *,
    reranked_docs: list[CitationSourceRow] | None = None,
    citation_rows_by_index: dict[int, CitationSourceRow] | None = None,
) -> AnswerSubquestionNodeInput:
    return AnswerSubquestionNodeInput(
        sub_question="What changed in VAT policy?",
        reranked_docs=reranked_docs or [],
        citation_rows_by_index=citation_rows_by_index or {},
        run_metadata=GraphRunMetadata(
            run_id="run-node-answer",
            trace_id="trace-node-answer",
            correlation_id="corr-node-answer",
        ),
    )


def test_run_answer_node_returns_no_doc_fallback_when_empty() -> None:
    called = False

    def _fake_generate_subanswer(**_kwargs):
        nonlocal called
        called = True
        return "unused"

    output = answer.run_answer_node(
        node_input=_node_input(),
        generate_subanswer_fn=_fake_generate_subanswer,
    )

    assert called is False
    assert output.sub_answer == "nothing relevant found"
    assert output.answerable is False
    assert output.verification_reason == "no_reranked_documents"
    assert output.citation_indices_used == []
    assert output.citation_rows_by_index == {}


def test_run_answer_node_returns_supported_answer_with_citation_rows() -> None:
    captured: dict[str, object] = {}
    docs = [
        CitationSourceRow(
            citation_index=1,
            rank=1,
            title="Policy baseline",
            source="wiki://policy",
            content="VAT changed in 2025.",
            document_id="doc-1",
        ),
        CitationSourceRow(
            citation_index=2,
            rank=2,
            title="Regional memo",
            source="wiki://memo",
            content="Regional exemptions were adjusted.",
            document_id="doc-2",
        ),
    ]

    def _fake_generate_subanswer(*, sub_question, reranked_retrieved_output, callbacks):
        captured["sub_question"] = sub_question
        captured["reranked_retrieved_output"] = reranked_retrieved_output
        captured["callbacks"] = callbacks
        return "VAT changed in 2025 [1][2]."

    callback_marker = object()
    output = answer.run_answer_node(
        node_input=_node_input(reranked_docs=docs),
        callbacks=[callback_marker],
        generate_subanswer_fn=_fake_generate_subanswer,
    )

    assert captured["sub_question"] == "What changed in VAT policy?"
    assert captured["callbacks"] == [callback_marker]
    assert "title=Policy baseline" in str(captured["reranked_retrieved_output"])

    assert output.sub_answer == "VAT changed in 2025 [1][2]."
    assert output.answerable is True
    assert output.verification_reason == "citation_supported"
    assert output.citation_indices_used == [1, 2]
    assert sorted(output.citation_rows_by_index.keys()) == [1, 2]
    assert output.citation_rows_by_index[2].document_id == "doc-2"


def test_run_answer_node_enforces_missing_citation_markers_contract() -> None:
    docs = [
        CitationSourceRow(
            citation_index=1,
            rank=1,
            title="Policy baseline",
            source="wiki://policy",
            content="VAT changed in 2025.",
            document_id="doc-1",
        )
    ]

    output = answer.run_answer_node(
        node_input=_node_input(reranked_docs=docs),
        generate_subanswer_fn=lambda **_kwargs: "VAT changed in 2025.",
    )

    assert output.sub_answer == "nothing relevant found"
    assert output.answerable is False
    assert output.verification_reason == "missing_citation_markers"
    assert output.citation_indices_used == []
    assert output.citation_rows_by_index == {}


def test_run_answer_node_enforces_missing_supporting_source_rows_contract() -> None:
    docs = [
        CitationSourceRow(
            citation_index=1,
            rank=1,
            title="Policy baseline",
            source="wiki://policy",
            content="VAT changed in 2025.",
            document_id="doc-1",
        )
    ]

    output = answer.run_answer_node(
        node_input=_node_input(reranked_docs=docs),
        generate_subanswer_fn=lambda **_kwargs: "VAT changed in 2025 [3].",
    )

    assert output.sub_answer == "nothing relevant found"
    assert output.answerable is False
    assert output.verification_reason == "missing_supporting_source_rows"
    assert output.citation_indices_used == []
    assert output.citation_rows_by_index == {}
