from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime.nodes import rerank
from schemas import CitationSourceRow, GraphRunMetadata, RerankNodeInput
from services.document_validation_service import RetrievedDocument
from services.reranker_service import RerankedDocumentScore, RerankerConfig


def _node_input(*, expanded_query: str = "", retrieved_docs: list[CitationSourceRow] | None = None) -> RerankNodeInput:
    return RerankNodeInput(
        sub_question="What changed in VAT policy?",
        expanded_query=expanded_query,
        retrieved_docs=retrieved_docs or [],
        run_metadata=GraphRunMetadata(
            run_id="run-node-rerank",
            trace_id="trace-node-rerank",
            correlation_id="corr-node-rerank",
        ),
    )


def test_run_rerank_node_reorders_and_remaps_document_ids() -> None:
    captured: dict[str, object] = {}
    docs = [
        CitationSourceRow(
            citation_index=1,
            rank=1,
            title="Policy baseline",
            source="wiki://policy",
            content="Policy text",
            document_id="doc-1",
        ),
        CitationSourceRow(
            citation_index=2,
            rank=2,
            title="Regional memo",
            source="wiki://memo",
            content="Regional text",
            document_id="doc-2",
        ),
    ]

    def _fake_rerank_documents(*, query, documents, config, callbacks):
        captured["query"] = query
        captured["documents"] = documents
        captured["config"] = config
        captured["callbacks"] = callbacks
        return [
            RerankedDocumentScore(
                document=RetrievedDocument(
                    rank=1,
                    title="Regional memo reranked",
                    source="wiki://memo",
                    content="Regional text",
                ),
                score=0.91,
                original_rank=2,
                reranked_rank=1,
            ),
            RerankedDocumentScore(
                document=RetrievedDocument(
                    rank=2,
                    title="Policy baseline reranked",
                    source="wiki://policy",
                    content="Policy text",
                ),
                score=0.77,
                original_rank=1,
                reranked_rank=2,
            ),
        ]

    callback_marker = object()
    config = RerankerConfig(enabled=True, top_n=5, model_name="ms-marco-MiniLM-L-12-v2")
    output = rerank.run_rerank_node(
        node_input=_node_input(expanded_query="VAT updates in 2025", retrieved_docs=docs),
        config=config,
        callbacks=[callback_marker],
        rerank_documents_fn=_fake_rerank_documents,
    )

    assert captured["query"] == "VAT updates in 2025"
    assert [item.rank for item in captured["documents"]] == [1, 2]
    assert captured["config"] == config
    assert captured["callbacks"] == [callback_marker]

    assert [item.citation_index for item in output.reranked_docs] == [1, 2]
    assert [item.rank for item in output.reranked_docs] == [1, 2]
    assert [item.document_id for item in output.reranked_docs] == ["doc-2", "doc-1"]
    assert output.reranked_docs[0].score == 0.91
    assert output.citation_rows_by_index[1].title == "Regional memo reranked"
    assert output.citation_rows_by_index[2].title == "Policy baseline reranked"


def test_run_rerank_node_uses_sub_question_when_expanded_query_blank() -> None:
    captured: dict[str, object] = {}

    def _fake_rerank_documents(*, query, documents, config, callbacks):
        captured["query"] = query
        _ = documents, config, callbacks
        return []

    rerank.run_rerank_node(
        node_input=_node_input(
            expanded_query="  ",
            retrieved_docs=[
                CitationSourceRow(
                    citation_index=1,
                    rank=1,
                    title="Policy baseline",
                    source="wiki://policy",
                    content="Policy text",
                    document_id="doc-1",
                )
            ],
        ),
        rerank_documents_fn=_fake_rerank_documents,
    )

    assert captured["query"] == "What changed in VAT policy?"


def test_run_rerank_node_returns_empty_output_when_no_candidates() -> None:
    called = False

    def _fake_rerank_documents(**_kwargs):
        nonlocal called
        called = True
        return []

    output = rerank.run_rerank_node(
        node_input=_node_input(),
        rerank_documents_fn=_fake_rerank_documents,
    )

    assert called is False
    assert output.reranked_docs == []
    assert output.citation_rows_by_index == {}
