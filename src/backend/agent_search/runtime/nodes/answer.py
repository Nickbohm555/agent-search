from __future__ import annotations

import logging
import re
from typing import Any, Callable

from schemas import AnswerSubquestionNodeInput, AnswerSubquestionNodeOutput, CitationSourceRow
from services.document_validation_service import RetrievedDocument, format_retrieved_documents
from services.subanswer_service import generate_subanswer
from services.subanswer_verification_service import SubanswerVerificationResult, verify_subanswer

logger = logging.getLogger(__name__)

_QUERY_LOG_MAX = 200
_ANSWER_SUBQUESTION_NO_SUPPORT_FALLBACK = "nothing relevant found"
_CITATION_INDEX_PATTERN = re.compile(r"\[(\d+)\]")


def _truncate_query(q: str) -> str:
    return q[: _QUERY_LOG_MAX] + "..." if len(q) > _QUERY_LOG_MAX else q


def _extract_citation_indices(answer: str) -> list[int]:
    if not answer:
        return []
    seen: set[int] = set()
    indices: list[int] = []
    for raw_index in _CITATION_INDEX_PATTERN.findall(answer):
        try:
            index = int(raw_index)
        except ValueError:
            continue
        if index <= 0 or index in seen:
            continue
        seen.add(index)
        indices.append(index)
    return indices


def _format_citation_rows_for_pipeline(rows: list[CitationSourceRow]) -> str:
    documents = [
        RetrievedDocument(
            rank=row.rank,
            title=row.title,
            source=row.source,
            content=row.content,
        )
        for row in rows
    ]
    return format_retrieved_documents(documents)


def run_answer_node(
    *,
    node_input: AnswerSubquestionNodeInput,
    callbacks: list[Any] | None = None,
    no_support_fallback: str = _ANSWER_SUBQUESTION_NO_SUPPORT_FALLBACK,
    format_citation_rows_for_pipeline_fn: Callable[[list[CitationSourceRow]], str] = _format_citation_rows_for_pipeline,
    generate_subanswer_fn: Callable[..., str] = generate_subanswer,
    verify_subanswer_fn: Callable[..., SubanswerVerificationResult] = verify_subanswer,
    extract_citation_indices_fn: Callable[[str], list[int]] = _extract_citation_indices,
    truncate_query_fn: Callable[[str], str] = _truncate_query,
) -> AnswerSubquestionNodeOutput:
    logger.info(
        "Subanswer node start sub_question=%s reranked_doc_count=%s run_id=%s trace_id=%s correlation_id=%s",
        truncate_query_fn(node_input.sub_question),
        len(node_input.reranked_docs),
        node_input.run_metadata.run_id,
        node_input.run_metadata.trace_id,
        node_input.run_metadata.correlation_id,
    )

    if not node_input.reranked_docs:
        logger.info(
            "Subanswer node fallback; no reranked docs sub_question=%s run_id=%s",
            truncate_query_fn(node_input.sub_question),
            node_input.run_metadata.run_id,
        )
        return AnswerSubquestionNodeOutput(
            sub_answer=no_support_fallback,
            citation_indices_used=[],
            answerable=False,
            verification_reason="no_reranked_documents",
            citation_rows_by_index={},
        )

    reranked_output = format_citation_rows_for_pipeline_fn(node_input.reranked_docs)
    generated_sub_answer = generate_subanswer_fn(
        sub_question=node_input.sub_question,
        reranked_retrieved_output=reranked_output,
        callbacks=callbacks,
    )
    verification = verify_subanswer_fn(
        sub_question=node_input.sub_question,
        sub_answer=generated_sub_answer,
        reranked_retrieved_output=reranked_output,
    )

    citation_rows = dict(node_input.citation_rows_by_index)
    if not citation_rows:
        citation_rows = {row.citation_index: row for row in node_input.reranked_docs}
    citation_indices_used = extract_citation_indices_fn(generated_sub_answer)
    supports_answer = bool(verification.answerable)
    invalid_indices = [index for index in citation_indices_used if index not in citation_rows]
    missing_citations = supports_answer and not citation_indices_used
    missing_support_rows = supports_answer and bool(citation_indices_used) and bool(invalid_indices)

    if missing_citations:
        supports_answer = False
        verification = SubanswerVerificationResult(
            answerable=False,
            reason="missing_citation_markers",
        )
    elif missing_support_rows:
        supports_answer = False
        verification = SubanswerVerificationResult(
            answerable=False,
            reason="missing_supporting_source_rows",
        )

    if not supports_answer:
        logger.info(
            "Subanswer node fallback; unsupported answer sub_question=%s reason=%s citation_indices=%s run_id=%s",
            truncate_query_fn(node_input.sub_question),
            verification.reason,
            citation_indices_used,
            node_input.run_metadata.run_id,
        )
        return AnswerSubquestionNodeOutput(
            sub_answer=no_support_fallback,
            citation_indices_used=[],
            answerable=False,
            verification_reason=verification.reason,
            citation_rows_by_index={},
        )

    supporting_rows = {
        index: citation_rows[index].model_copy(deep=True)
        for index in citation_indices_used
        if index in citation_rows
    }
    logger.info(
        "Subanswer node complete sub_question=%s answer_len=%s citation_count=%s run_id=%s",
        truncate_query_fn(node_input.sub_question),
        len(generated_sub_answer),
        len(citation_indices_used),
        node_input.run_metadata.run_id,
    )
    return AnswerSubquestionNodeOutput(
        sub_answer=generated_sub_answer,
        citation_indices_used=citation_indices_used,
        answerable=True,
        verification_reason=verification.reason,
        citation_rows_by_index=supporting_rows,
    )


__all__ = ["run_answer_node"]
