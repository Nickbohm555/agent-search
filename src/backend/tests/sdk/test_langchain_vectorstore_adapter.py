from __future__ import annotations

import logging
import sys
from pathlib import Path

from langchain_core.documents import Document

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.vectorstore.langchain_adapter import LangChainVectorStoreAdapter


def test_similarity_search_passes_filter_and_coerces_k(caplog) -> None:
    captured: dict[str, object] = {}
    expected_doc = Document(page_content="policy", metadata={"source": "wiki://policy"})

    class _Store:
        def similarity_search(self, query: str, k: int, filter=None):
            captured["query"] = query
            captured["k"] = k
            captured["filter"] = filter
            return [expected_doc]

    adapter = LangChainVectorStoreAdapter(_Store())
    with caplog.at_level(logging.INFO):
        docs = adapter.similarity_search("nato policy", k=0, filter={"source": "wiki://nato"})

    assert docs == [expected_doc]
    assert captured == {"query": "nato policy", "k": 1, "filter": {"source": "wiki://nato"}}
    assert "mode=with_filter" in caplog.text


def test_similarity_search_falls_back_when_store_has_no_filter_param(caplog) -> None:
    captured: dict[str, object] = {}
    expected_doc = Document(page_content="fallback", metadata={})

    class _Store:
        def similarity_search(self, query: str, k: int):
            captured["query"] = query
            captured["k"] = k
            return [expected_doc]

    adapter = LangChainVectorStoreAdapter(_Store())
    with caplog.at_level(logging.INFO):
        docs = adapter.similarity_search("query text", k=3, filter={"source": "wiki://ignored"})

    assert docs == [expected_doc]
    assert captured == {"query": "query text", "k": 3}
    assert "mode=without_filter" in caplog.text


def test_relevance_search_uses_scores_when_supported(caplog) -> None:
    captured: dict[str, object] = {}
    expected_doc = Document(page_content="scored", metadata={})

    class _Store:
        def similarity_search_with_relevance_scores(
            self,
            query: str,
            k: int,
            score_threshold: float | None = None,
            filter=None,
        ):
            captured["query"] = query
            captured["k"] = k
            captured["score_threshold"] = score_threshold
            captured["filter"] = filter
            return [(expected_doc, 0.91)]

    adapter = LangChainVectorStoreAdapter(_Store())
    with caplog.at_level(logging.INFO):
        docs_with_scores = adapter.similarity_search_with_relevance_scores(
            "scored query",
            k=2,
            score_threshold=0.5,
            filter={"source": "wiki://doc"},
        )

    assert docs_with_scores == [(expected_doc, 0.91)]
    assert captured == {
        "query": "scored query",
        "k": 2,
        "score_threshold": 0.5,
        "filter": {"source": "wiki://doc"},
    }
    assert "mode=with_scores" in caplog.text


def test_relevance_search_falls_back_to_similarity_when_scores_unavailable(caplog) -> None:
    expected_doc = Document(page_content="fallback score", metadata={})

    class _Store:
        def similarity_search(self, query: str, k: int, filter=None):
            _ = query, filter
            return [expected_doc][:k]

    adapter = LangChainVectorStoreAdapter(_Store())
    with caplog.at_level(logging.INFO):
        docs_with_scores = adapter.similarity_search_with_relevance_scores("fallback score query", k=2)

    assert docs_with_scores == [(expected_doc, 1.0)]
    assert "mode=similarity_search" in caplog.text


def test_relevance_search_falls_back_when_score_method_is_unimplemented(caplog) -> None:
    expected_doc = Document(page_content="fallback from not implemented", metadata={})

    class _Store:
        def similarity_search(self, query: str, k: int, filter=None):
            _ = query, filter
            return [expected_doc][:k]

        def similarity_search_with_relevance_scores(self, query: str, k: int, score_threshold=None, filter=None):
            _ = query, k, score_threshold, filter
            raise NotImplementedError

    adapter = LangChainVectorStoreAdapter(_Store())
    with caplog.at_level(logging.INFO):
        docs_with_scores = adapter.similarity_search_with_relevance_scores("fallback score query", k=2)

    assert docs_with_scores == [(expected_doc, 1.0)]
    assert "mode=not_implemented" in caplog.text
