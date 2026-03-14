from __future__ import annotations

import logging
import os
from typing import Any, Callable

from agent_search.vectorstore.protocol import (
    VectorStoreProtocol,
    assert_vector_store_compatible,
)
from schemas import CitationSourceRow, SearchNodeInput, SearchNodeOutput
from services.vector_store_service import (
    CITATION_DOCUMENT_ID_METADATA_KEY,
    CITATION_SOURCE_METADATA_KEY,
    CITATION_TITLE_METADATA_KEY,
    search_documents_for_queries,
)

logger = logging.getLogger(__name__)

_QUERY_LOG_MAX = 200
_SEARCH_NODE_K_FETCH = max(1, int(os.getenv("SEARCH_NODE_K_FETCH", "10")))
_SEARCH_NODE_SCORE_THRESHOLD_RAW = os.getenv("SEARCH_NODE_SCORE_THRESHOLD", "0.0")
try:
    _SEARCH_NODE_SCORE_THRESHOLD = (
        float(_SEARCH_NODE_SCORE_THRESHOLD_RAW) if _SEARCH_NODE_SCORE_THRESHOLD_RAW not in (None, "") else None
    )
except ValueError:
    _SEARCH_NODE_SCORE_THRESHOLD = None
_SEARCH_NODE_MERGED_CAP = max(1, int(os.getenv("SEARCH_NODE_MERGED_CAP", "30")))


def _truncate_query(q: str) -> str:
    return q[: _QUERY_LOG_MAX] + "..." if len(q) > _QUERY_LOG_MAX else q


def _normalize_search_queries(*, sub_question: str, expanded_queries: list[str]) -> list[str]:
    candidates = [sub_question, *expanded_queries]
    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        query = (candidate or "").strip()
        if not query:
            continue
        lowered = query.casefold()
        if lowered in seen:
            continue
        normalized.append(query)
        seen.add(lowered)
    return normalized


def _build_document_identity(
    *,
    document_id: str,
    source: str,
    content: str,
) -> str:
    if document_id:
        return f"document_id:{document_id}"
    normalized_source = source.strip().casefold()
    normalized_content = content.strip()
    if normalized_source:
        return f"source_content:{normalized_source}|{normalized_content}"
    return f"content:{normalized_content}"


def _build_citation_row_from_document(*, document: Any, rank: int) -> CitationSourceRow:
    metadata = document.metadata or {}
    title = str(metadata.get(CITATION_TITLE_METADATA_KEY) or "").strip()
    source = str(metadata.get(CITATION_SOURCE_METADATA_KEY) or "").strip()
    content = str(getattr(document, "page_content", "") or "").strip()
    document_id = str(metadata.get(CITATION_DOCUMENT_ID_METADATA_KEY) or getattr(document, "id", "") or "").strip()
    return CitationSourceRow(
        citation_index=rank,
        rank=rank,
        title=title,
        source=source,
        content=content,
        document_id=document_id,
        score=None,
    )


def run_search_node(
    *,
    node_input: SearchNodeInput,
    vector_store: VectorStoreProtocol,
    k_fetch: int | None = None,
    score_threshold: float | None = None,
    merged_cap: int | None = None,
    search_documents_for_queries_fn: Callable[..., dict[str, list[Any]]] = search_documents_for_queries,
    assert_vector_store_compatible_fn: Callable[[Any], VectorStoreProtocol] = assert_vector_store_compatible,
    truncate_query_fn: Callable[[str], str] = _truncate_query,
    default_k_fetch: int = _SEARCH_NODE_K_FETCH,
    default_score_threshold: float | None = _SEARCH_NODE_SCORE_THRESHOLD,
    default_merged_cap: int = _SEARCH_NODE_MERGED_CAP,
) -> SearchNodeOutput:
    compatible_store = assert_vector_store_compatible_fn(vector_store)
    effective_k_fetch = max(1, k_fetch or default_k_fetch)
    effective_score_threshold = default_score_threshold if score_threshold is None else score_threshold
    effective_merged_cap = default_merged_cap if merged_cap is None else merged_cap
    normalized_queries = _normalize_search_queries(
        sub_question=node_input.sub_question,
        expanded_queries=node_input.expanded_queries,
    )
    logger.info(
        "Search node start sub_question=%s expanded_query_count=%s normalized_query_count=%s k_fetch=%s run_id=%s trace_id=%s correlation_id=%s",
        truncate_query_fn(node_input.sub_question),
        len(node_input.expanded_queries),
        len(normalized_queries),
        effective_k_fetch,
        node_input.run_metadata.run_id,
        node_input.run_metadata.trace_id,
        node_input.run_metadata.correlation_id,
    )
    if not normalized_queries:
        logger.warning(
            "Search node skipped; no valid queries sub_question=%s run_id=%s",
            truncate_query_fn(node_input.sub_question),
            node_input.run_metadata.run_id,
        )
        return SearchNodeOutput()

    documents_by_query = search_documents_for_queries_fn(
        vector_store=compatible_store,
        queries=normalized_queries,
        k=effective_k_fetch,
        score_threshold=effective_score_threshold,
    )
    merged_rows: list[CitationSourceRow] = []
    retrieval_provenance: list[dict[str, Any]] = []
    seen_document_identities: dict[str, int] = {}

    def _extract_score(document: Any) -> float | None:
        if document is None:
            return None
        metadata = getattr(document, "metadata", {}) or {}
        score = metadata.get("score")
        return float(score) if isinstance(score, (int, float)) else None

    for query_index, query in enumerate(normalized_queries, start=1):
        docs_for_query = documents_by_query.get(query, [])
        for query_rank, document in enumerate(docs_for_query, start=1):
            row = _build_citation_row_from_document(document=document, rank=len(merged_rows) + 1)
            row.score = _extract_score(document)
            document_identity = _build_document_identity(
                document_id=row.document_id,
                source=row.source,
                content=row.content,
            )
            deduped = document_identity in seen_document_identities
            retrieval_provenance.append(
                {
                    "query": query,
                    "query_index": query_index,
                    "query_rank": query_rank,
                    "document_identity": document_identity,
                    "document_id": row.document_id,
                    "source": row.source,
                    "deduped": deduped,
                }
            )
            if deduped:
                existing_index = seen_document_identities[document_identity]
                existing_row = merged_rows[existing_index]
                existing_score = existing_row.score if existing_row.score is not None else float("-inf")
                candidate_score = row.score if row.score is not None else float("-inf")
                if candidate_score > existing_score:
                    existing_row.score = row.score
                continue
            seen_document_identities[document_identity] = len(merged_rows)
            row.rank = len(merged_rows) + 1
            row.citation_index = len(merged_rows) + 1
            merged_rows.append(row)

    if effective_merged_cap and len(merged_rows) > effective_merged_cap:
        merged_rows = merged_rows[:effective_merged_cap]
        for index, row in enumerate(merged_rows, start=1):
            row.rank = index
            row.citation_index = index

    citation_rows_by_index = {item.citation_index: item for item in merged_rows}
    logger.info(
        "Search node complete sub_question=%s query_count=%s raw_candidates=%s merged_candidates=%s run_id=%s",
        truncate_query_fn(node_input.sub_question),
        len(normalized_queries),
        sum(len(documents_by_query.get(query, [])) for query in normalized_queries),
        len(merged_rows),
        node_input.run_metadata.run_id,
    )
    return SearchNodeOutput(
        retrieved_docs=merged_rows,
        retrieval_provenance=retrieval_provenance,
        citation_rows_by_index=citation_rows_by_index,
    )


__all__ = ["run_search_node"]
