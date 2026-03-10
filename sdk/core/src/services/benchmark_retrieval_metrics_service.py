from __future__ import annotations

import logging
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from db import SessionLocal
from models import BenchmarkResult, BenchmarkRetrievalMetric, BenchmarkRun

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievalMetricsEvaluation:
    recall_at_k: float | None
    mrr: float | None
    ndcg: float | None
    retrieved_document_ids: list[str]
    relevant_document_ids: list[str]
    k: int
    label_source: str | None


class BenchmarkRetrievalMetricsService:
    """Compute and persist benchmark retrieval diagnostics for one result."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] = SessionLocal,
        default_k: int = 10,
    ) -> None:
        self._session_factory = session_factory
        self._default_k = max(1, int(default_k))

    def evaluate_and_persist(
        self,
        *,
        result_id: int,
        relevant_document_ids: Sequence[str] | None = None,
        k: int | None = None,
        label_source: str | None = None,
    ) -> BenchmarkRetrievalMetric:
        with self._session_factory() as session:
            result = session.get(BenchmarkResult, result_id)
            if result is None:
                raise ValueError(f"Benchmark result not found for retrieval diagnostics result_id={result_id}")

            run = session.get(BenchmarkRun, result.run_id)
            resolved_labels = self._resolve_relevant_labels(
                explicit_labels=relevant_document_ids,
                run_metadata=run.run_metadata if run is not None else None,
                mode=result.mode,
                question_id=result.question_id,
            )
            effective_k = max(1, int(k if k is not None else self._default_k))
            evaluation = self.evaluate(
                citations=result.citations,
                relevant_document_ids=resolved_labels,
                k=effective_k,
                label_source=label_source or ("run_metadata" if resolved_labels else None),
            )

            row = session.scalar(
                select(BenchmarkRetrievalMetric).where(
                    BenchmarkRetrievalMetric.run_id == result.run_id,
                    BenchmarkRetrievalMetric.mode == result.mode,
                    BenchmarkRetrievalMetric.question_id == result.question_id,
                )
            )
            if row is None:
                row = BenchmarkRetrievalMetric(
                    run_id=result.run_id,
                    result_id=result.id,
                    mode=result.mode,
                    question_id=result.question_id,
                )
                session.add(row)

            row.result_id = result.id
            row.recall_at_k = evaluation.recall_at_k
            row.mrr = evaluation.mrr
            row.ndcg = evaluation.ndcg
            row.k = evaluation.k
            row.retrieved_document_ids = evaluation.retrieved_document_ids
            row.relevant_document_ids = evaluation.relevant_document_ids
            row.label_source = evaluation.label_source
            session.commit()
            session.refresh(row)
            logger.info(
                "Benchmark retrieval diagnostics persisted run_id=%s mode=%s question_id=%s k=%s has_labels=%s recall_at_k=%s mrr=%s ndcg=%s",
                row.run_id,
                row.mode,
                row.question_id,
                row.k,
                bool(row.relevant_document_ids),
                row.recall_at_k,
                row.mrr,
                row.ndcg,
            )
            return row

    def evaluate(
        self,
        *,
        citations: object,
        relevant_document_ids: Sequence[str] | None,
        k: int,
        label_source: str | None = None,
    ) -> RetrievalMetricsEvaluation:
        retrieved_ids = self._extract_retrieved_document_ids(citations)
        relevant_ids = self._normalize_document_ids(relevant_document_ids)
        metrics_k = max(1, int(k))

        if not relevant_ids:
            logger.info(
                "Benchmark retrieval diagnostics skipped metric scoring due to missing labels retrieved_count=%s k=%s",
                len(retrieved_ids),
                metrics_k,
            )
            return RetrievalMetricsEvaluation(
                recall_at_k=None,
                mrr=None,
                ndcg=None,
                retrieved_document_ids=retrieved_ids,
                relevant_document_ids=[],
                k=metrics_k,
                label_source=None,
            )

        relevant_set = set(relevant_ids)
        top_k_ids = retrieved_ids[:metrics_k]
        hits = sum(1 for doc_id in top_k_ids if doc_id in relevant_set)
        recall_at_k = hits / len(relevant_set)

        reciprocal_rank = 0.0
        for index, doc_id in enumerate(retrieved_ids, start=1):
            if doc_id in relevant_set:
                reciprocal_rank = 1.0 / float(index)
                break

        dcg = 0.0
        for index, doc_id in enumerate(top_k_ids, start=1):
            if doc_id in relevant_set:
                dcg += 1.0 / math.log2(index + 1)
        ideal_hits = min(len(relevant_set), metrics_k)
        idcg = sum(1.0 / math.log2(index + 1) for index in range(1, ideal_hits + 1))
        ndcg = (dcg / idcg) if idcg > 0.0 else 0.0

        logger.info(
            "Benchmark retrieval diagnostics evaluated retrieved_count=%s relevant_count=%s k=%s recall_at_k=%.4f mrr=%.4f ndcg=%.4f",
            len(retrieved_ids),
            len(relevant_set),
            metrics_k,
            recall_at_k,
            reciprocal_rank,
            ndcg,
        )
        return RetrievalMetricsEvaluation(
            recall_at_k=recall_at_k,
            mrr=reciprocal_rank,
            ndcg=ndcg,
            retrieved_document_ids=retrieved_ids,
            relevant_document_ids=relevant_ids,
            k=metrics_k,
            label_source=label_source,
        )

    @staticmethod
    def _normalize_document_ids(document_ids: Sequence[str] | None) -> list[str]:
        if not document_ids:
            return []
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in document_ids:
            if not isinstance(raw, str):
                continue
            candidate = raw.strip()
            if not candidate or candidate in seen:
                continue
            normalized.append(candidate)
            seen.add(candidate)
        return normalized

    @classmethod
    def _extract_retrieved_document_ids(cls, citations: object) -> list[str]:
        if not isinstance(citations, list):
            return []

        sortable_rows: list[tuple[int, int, str]] = []
        for index, entry in enumerate(citations):
            if not isinstance(entry, dict):
                continue
            document_id = entry.get("document_id")
            if not isinstance(document_id, str) or not document_id.strip():
                continue
            rank_value = entry.get("rank")
            rank = rank_value if isinstance(rank_value, int) and rank_value > 0 else 10_000 + index
            sortable_rows.append((rank, index, document_id.strip()))

        sortable_rows.sort()
        unique_ids: list[str] = []
        seen: set[str] = set()
        for _, _, document_id in sortable_rows:
            if document_id in seen:
                continue
            unique_ids.append(document_id)
            seen.add(document_id)
        return unique_ids

    def _resolve_relevant_labels(
        self,
        *,
        explicit_labels: Sequence[str] | None,
        run_metadata: object,
        mode: str,
        question_id: str,
    ) -> list[str]:
        explicit = self._normalize_document_ids(explicit_labels)
        if explicit:
            return explicit

        if not isinstance(run_metadata, Mapping):
            return []
        retrieval_labels = run_metadata.get("retrieval_labels")
        if not isinstance(retrieval_labels, Mapping):
            return []

        by_question = retrieval_labels.get(question_id)
        labels = self._normalize_document_ids(self._coerce_labels_payload(by_question))
        if labels:
            return labels

        by_mode = retrieval_labels.get(mode)
        if isinstance(by_mode, Mapping):
            labels = self._normalize_document_ids(self._coerce_labels_payload(by_mode.get(question_id)))
            if labels:
                return labels

        default_labels = retrieval_labels.get("default")
        return self._normalize_document_ids(self._coerce_labels_payload(default_labels))

    @staticmethod
    def _coerce_labels_payload(payload: object) -> Sequence[str] | None:
        if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
            return [str(item) for item in payload if isinstance(item, str)]
        if isinstance(payload, Mapping):
            for key in ("relevant_document_ids", "document_ids", "labels"):
                value = payload.get(key)
                if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                    return [str(item) for item in value if isinstance(item, str)]
        return None
