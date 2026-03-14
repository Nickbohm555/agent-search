from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.errors import SDKConfigurationError
from agent_search.runtime.nodes import search
from schemas import GraphRunMetadata, SearchNodeInput
from services.vector_store_service import (
    CITATION_DOCUMENT_ID_METADATA_KEY,
    CITATION_SOURCE_METADATA_KEY,
    CITATION_TITLE_METADATA_KEY,
)


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None):
        _ = query, k, filter
        return []


class _MissingVectorStoreMethod:
    pass


class _Doc:
    def __init__(
        self,
        *,
        doc_id: str,
        title: str,
        source: str,
        content: str,
        score: float | None = None,
        include_legacy_only: bool = False,
    ):
        self.id = doc_id
        metadata: dict[str, object] = {}
        if include_legacy_only:
            metadata.update({"title": title, "source": source})
        else:
            metadata.update(
                {
                    CITATION_TITLE_METADATA_KEY: title,
                    CITATION_SOURCE_METADATA_KEY: source,
                    CITATION_DOCUMENT_ID_METADATA_KEY: doc_id,
                }
            )
        if score is not None:
            metadata["score"] = score
        self.metadata = metadata
        self.page_content = content


def _node_input(
    sub_question: str = "What changed in VAT policy?",
    expanded_queries: list[str] | None = None,
) -> SearchNodeInput:
    return SearchNodeInput(
        sub_question=sub_question,
        expanded_queries=expanded_queries or [],
        run_metadata=GraphRunMetadata(
            run_id="run-node-search",
            trace_id="trace-node-search",
            correlation_id="corr-node-search",
        ),
    )


def test_run_search_node_merges_and_dedupes_multi_query_results() -> None:
    captured: dict[str, object] = {}

    def fake_search_documents_for_queries(*, vector_store, queries, k, score_threshold):
        captured["vector_store"] = vector_store
        captured["queries"] = queries
        captured["k"] = k
        captured["score_threshold"] = score_threshold
        return {
            "What changed in VAT policy?": [
                _Doc(
                    doc_id="doc-1",
                    title="Policy Doc",
                    source="wiki://policy",
                    content="Policy changed in 2025.",
                    score=0.45,
                ),
                _Doc(doc_id="", title="Regional Memo", source="wiki://memo", content="Regional changes by country."),
            ],
            "VAT policy updates 2025": [
                _Doc(
                    doc_id="doc-1",
                    title="Policy Doc Duplicate",
                    source="wiki://policy",
                    content="Duplicate by id.",
                    score=0.83,
                ),
                _Doc(
                    doc_id="",
                    title="Regional Memo Duplicate",
                    source="wiki://memo",
                    content="Regional changes by country.",
                ),
                _Doc(doc_id="doc-4", title="Timeline", source="wiki://timeline", content="Timeline details."),
            ],
            "VAT changes by region": [
                _Doc(doc_id="doc-5", title="Region Breakdown", source="wiki://regions", content="Region-by-region notes.")
            ],
        }

    store = _CompatibleVectorStore()
    output = search.run_search_node(
        node_input=_node_input(
            expanded_queries=[
                "VAT policy updates 2025",
                "VAT changes by region",
            ]
        ),
        vector_store=store,
        k_fetch=7,
        score_threshold=0.1,
        search_documents_for_queries_fn=fake_search_documents_for_queries,
    )

    assert captured == {
        "vector_store": store,
        "queries": [
            "What changed in VAT policy?",
            "VAT policy updates 2025",
            "VAT changes by region",
        ],
        "k": 7,
        "score_threshold": 0.1,
    }
    assert [item.document_id for item in output.retrieved_docs] == ["doc-1", "", "doc-4", "doc-5"]
    assert [item.rank for item in output.retrieved_docs] == [1, 2, 3, 4]
    assert [item.citation_index for item in output.retrieved_docs] == [1, 2, 3, 4]
    assert output.retrieved_docs[0].score == 0.83
    assert len(output.retrieval_provenance) == 6
    assert sum(1 for item in output.retrieval_provenance if item["deduped"]) == 2
    assert output.citation_rows_by_index[1].title == "Policy Doc"
    assert output.citation_rows_by_index[3].title == "Timeline"


def test_run_search_node_uses_explicit_citation_metadata_keys_only() -> None:
    def fake_search_documents_for_queries(*, vector_store, queries, k, score_threshold):
        _ = vector_store, queries, k, score_threshold
        return {
            "What changed in VAT policy?": [
                _Doc(
                    doc_id="doc-legacy",
                    title="Legacy Title",
                    source="wiki://legacy",
                    content="Legacy metadata only.",
                    include_legacy_only=True,
                ),
                _Doc(
                    doc_id="doc-explicit",
                    title="Explicit Title",
                    source="wiki://explicit",
                    content="Explicit citation metadata.",
                ),
            ]
        }

    output = search.run_search_node(
        node_input=_node_input(),
        vector_store=_CompatibleVectorStore(),
        search_documents_for_queries_fn=fake_search_documents_for_queries,
    )

    assert [item.document_id for item in output.retrieved_docs] == ["doc-legacy", "doc-explicit"]
    assert output.retrieved_docs[0].title == ""
    assert output.retrieved_docs[0].source == ""
    assert output.retrieved_docs[1].title == "Explicit Title"
    assert output.retrieved_docs[1].source == "wiki://explicit"


def test_run_search_node_returns_empty_output_when_no_queries() -> None:
    called = False

    def fake_search_documents_for_queries(**_kwargs):
        nonlocal called
        called = True
        return {}

    output = search.run_search_node(
        node_input=_node_input(sub_question="   "),
        vector_store=_CompatibleVectorStore(),
        search_documents_for_queries_fn=fake_search_documents_for_queries,
    )

    assert called is False
    assert output.retrieved_docs == []
    assert output.retrieval_provenance == []
    assert output.citation_rows_by_index == {}


def test_run_search_node_rejects_incompatible_vector_store() -> None:
    try:
        search.run_search_node(
            node_input=_node_input(),
            vector_store=_MissingVectorStoreMethod(),
        )
    except SDKConfigurationError as exc:
        assert str(exc) == "vector_store must implement similarity_search(query, k, filter=None)."
    else:
        raise AssertionError("Expected SDKConfigurationError for invalid vector store")
