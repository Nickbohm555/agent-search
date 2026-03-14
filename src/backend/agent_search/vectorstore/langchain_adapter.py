from __future__ import annotations

import inspect
import logging
from typing import Any

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class LangChainVectorStoreAdapter:
    """Adapter exposing a stable retrieval interface over LangChain vector stores."""

    def __init__(self, store: Any) -> None:
        self._store = store

    def similarity_search(
        self,
        query: str,
        k: int,
        filter: dict[str, Any] | None = None,
    ) -> list[Document]:
        safe_k = max(1, k)
        method = getattr(self._store, "similarity_search", None)
        if not callable(method):
            raise TypeError("Wrapped store must implement callable similarity_search")

        try:
            documents = method(query, k=safe_k, filter=filter)
            logger.info(
                "LangChain adapter similarity_search query_len=%s k=%s has_filter=%s results=%s mode=with_filter",
                len(query),
                safe_k,
                filter is not None,
                len(documents),
            )
            return documents
        except TypeError:
            documents = method(query, k=safe_k)
            logger.info(
                "LangChain adapter similarity_search fallback query_len=%s k=%s has_filter=%s results=%s mode=without_filter",
                len(query),
                safe_k,
                filter is not None,
                len(documents),
            )
            return documents

    def similarity_search_with_relevance_scores(
        self,
        query: str,
        k: int,
        score_threshold: float | None = None,
        filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        safe_k = max(1, k)
        method = getattr(self._store, "similarity_search_with_relevance_scores", None)

        if callable(method):
            kwargs: dict[str, Any] = {"k": safe_k}
            if score_threshold is not None:
                kwargs["score_threshold"] = score_threshold
            if filter is not None:
                try:
                    signature = inspect.signature(method)
                except (TypeError, ValueError):
                    signature = None
                if signature is None or "filter" in signature.parameters:
                    kwargs["filter"] = filter

            try:
                docs_with_scores = method(query, **kwargs)
                logger.info(
                    "LangChain adapter relevance_search query_len=%s k=%s score_threshold=%s has_filter=%s results=%s mode=with_scores",
                    len(query),
                    safe_k,
                    score_threshold,
                    filter is not None,
                    len(docs_with_scores),
                )
                return docs_with_scores
            except NotImplementedError:
                logger.info(
                    "LangChain adapter relevance_search fallback query_len=%s k=%s score_threshold=%s has_filter=%s mode=not_implemented",
                    len(query),
                    safe_k,
                    score_threshold,
                    filter is not None,
                )

        documents = self.similarity_search(query, k=safe_k, filter=filter)
        logger.info(
            "LangChain adapter relevance_search fallback query_len=%s k=%s score_threshold=%s has_filter=%s results=%s mode=similarity_search",
            len(query),
            safe_k,
            score_threshold,
            filter is not None,
            len(documents),
        )
        return [(document, 1.0) for document in documents]
