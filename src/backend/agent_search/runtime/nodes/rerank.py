from __future__ import annotations

import logging
from typing import Any, Callable

from schemas import CitationSourceRow, RerankNodeInput, RerankNodeOutput
from services.document_validation_service import RetrievedDocument
from services.reranker_service import (
    RerankerConfig,
    build_reranker_config_from_env,
    rerank_documents,
)

logger = logging.getLogger(__name__)

_QUERY_LOG_MAX = 200
_RERANKER_CONFIG = build_reranker_config_from_env()


def _truncate_query(q: str) -> str:
    return q[: _QUERY_LOG_MAX] + "..." if len(q) > _QUERY_LOG_MAX else q


def _to_retrieved_documents(rows: list[CitationSourceRow]) -> list[RetrievedDocument]:
    return [
        RetrievedDocument(
            rank=row.rank,
            title=row.title,
            source=row.source,
            content=row.content,
        )
        for row in rows
    ]


def run_rerank_node(
    *,
    node_input: RerankNodeInput,
    config: RerankerConfig | None = None,
    callbacks: list[Any] | None = None,
    default_config: RerankerConfig = _RERANKER_CONFIG,
    rerank_documents_fn: Callable[..., list[Any]] = rerank_documents,
    to_retrieved_documents_fn: Callable[[list[CitationSourceRow]], list[RetrievedDocument]] = _to_retrieved_documents,
    truncate_query_fn: Callable[[str], str] = _truncate_query,
) -> RerankNodeOutput:
    effective_config = config or default_config
    rerank_query = (node_input.expanded_query or "").strip() or node_input.sub_question
    logger.info(
        "Rerank node start sub_question=%s candidate_count=%s enabled=%s top_n=%s model=%s run_id=%s trace_id=%s correlation_id=%s",
        truncate_query_fn(node_input.sub_question),
        len(node_input.retrieved_docs),
        effective_config.enabled,
        effective_config.top_n,
        effective_config.model_name,
        node_input.run_metadata.run_id,
        node_input.run_metadata.trace_id,
        node_input.run_metadata.correlation_id,
    )
    if not node_input.retrieved_docs:
        logger.info(
            "Rerank node skipped; no retrieved candidates sub_question=%s run_id=%s",
            truncate_query_fn(node_input.sub_question),
            node_input.run_metadata.run_id,
        )
        return RerankNodeOutput()

    original_by_rank = {row.rank: row for row in node_input.retrieved_docs}
    reranked_scores = rerank_documents_fn(
        query=rerank_query,
        documents=to_retrieved_documents_fn(node_input.retrieved_docs),
        config=effective_config,
        callbacks=callbacks,
    )

    reranked_docs: list[CitationSourceRow] = []
    for new_rank, reranked in enumerate(reranked_scores, start=1):
        original_row = original_by_rank.get(reranked.original_rank)
        reranked_docs.append(
            CitationSourceRow(
                citation_index=new_rank,
                rank=new_rank,
                title=reranked.document.title,
                source=reranked.document.source,
                content=reranked.document.content,
                document_id=original_row.document_id if original_row is not None else "",
                score=reranked.score,
            )
        )

    citation_rows_by_index = {row.citation_index: row for row in reranked_docs}
    logger.info(
        "Rerank node complete sub_question=%s candidates_before=%s candidates_after=%s run_id=%s",
        truncate_query_fn(node_input.sub_question),
        len(node_input.retrieved_docs),
        len(reranked_docs),
        node_input.run_metadata.run_id,
    )
    return RerankNodeOutput(
        reranked_docs=reranked_docs,
        citation_rows_by_index=citation_rows_by_index,
    )


__all__ = ["run_rerank_node"]
