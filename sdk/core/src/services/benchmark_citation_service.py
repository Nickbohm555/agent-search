from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from db import SessionLocal
from models import BenchmarkCitationScore, BenchmarkCitationVerification, BenchmarkResult

logger = logging.getLogger(__name__)

_CITATION_PATTERN = re.compile(r"\[(\d+)\]")
_SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+|\n+")
_TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}")
_STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "this",
    "from",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "into",
    "about",
    "their",
    "they",
    "them",
    "than",
    "then",
    "also",
}


@dataclass(frozen=True)
class CitationVerification:
    citation_marker: str
    citation_index: int
    claim_text: str
    citation_found: bool
    is_supported: bool
    support_label: str
    support_evidence: str | None
    verification_payload: dict[str, Any]


@dataclass(frozen=True)
class CitationEvaluation:
    citation_presence_rate: float
    basic_support_rate: float
    evaluator_version: str
    total_citation_count: int
    found_citation_count: int
    supported_citation_count: int
    verifications: list[CitationVerification]


class BenchmarkCitationService:
    """Deterministic citation quality evaluator for benchmark answers."""

    def __init__(self, *, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    def evaluate_and_persist(self, *, result_id: int, evaluator_version: str = "v1") -> BenchmarkCitationScore:
        with self._session_factory() as session:
            result = session.get(BenchmarkResult, result_id)
            if result is None:
                raise ValueError(f"Benchmark result not found for citation scoring result_id={result_id}")

            evaluation = self.evaluate(
                answer_payload=result.answer_payload,
                citations=result.citations,
                evaluator_version=evaluator_version,
            )
            row = session.scalar(
                select(BenchmarkCitationScore).where(
                    BenchmarkCitationScore.run_id == result.run_id,
                    BenchmarkCitationScore.mode == result.mode,
                    BenchmarkCitationScore.question_id == result.question_id,
                )
            )
            if row is None:
                row = BenchmarkCitationScore(
                    run_id=result.run_id,
                    result_id=result.id,
                    mode=result.mode,
                    question_id=result.question_id,
                )
                session.add(row)

            row.result_id = result.id
            row.citation_presence_rate = evaluation.citation_presence_rate
            row.basic_support_rate = evaluation.basic_support_rate
            row.evaluator_version = evaluation.evaluator_version
            row.total_citation_count = evaluation.total_citation_count
            row.found_citation_count = evaluation.found_citation_count
            row.supported_citation_count = evaluation.supported_citation_count
            session.flush()

            session.execute(
                delete(BenchmarkCitationVerification).where(BenchmarkCitationVerification.citation_score_id == row.id)
            )
            for verification in evaluation.verifications:
                session.add(
                    BenchmarkCitationVerification(
                        citation_score_id=row.id,
                        run_id=result.run_id,
                        result_id=result.id,
                        mode=result.mode,
                        question_id=result.question_id,
                        citation_marker=verification.citation_marker,
                        citation_index=verification.citation_index,
                        claim_text=verification.claim_text,
                        citation_found=verification.citation_found,
                        is_supported=verification.is_supported,
                        support_label=verification.support_label,
                        support_evidence=verification.support_evidence,
                        verification_payload=verification.verification_payload,
                        verification_type="citation_support_v1",
                    )
                )

            session.commit()
            session.refresh(row)
            logger.info(
                "Benchmark citation persisted run_id=%s mode=%s question_id=%s presence=%.4f support=%.4f verifications=%s",
                row.run_id,
                row.mode,
                row.question_id,
                row.citation_presence_rate,
                row.basic_support_rate,
                len(evaluation.verifications),
            )
            return row

    def evaluate(
        self,
        *,
        answer_payload: dict[str, Any] | None,
        citations: list[dict[str, Any]] | None,
        evaluator_version: str = "v1",
    ) -> CitationEvaluation:
        answer_text = self._extract_answer_text(answer_payload)
        references = self._extract_references(answer_text)
        citation_map = self._build_citation_map(citations)

        verifications: list[CitationVerification] = []
        found_count = 0
        supported_count = 0
        for citation_index, claim_text in references:
            marker = f"[{citation_index}]"
            citation_row = citation_map.get(citation_index)
            if citation_row is None:
                verifications.append(
                    CitationVerification(
                        citation_marker=marker,
                        citation_index=citation_index,
                        claim_text=claim_text,
                        citation_found=False,
                        is_supported=False,
                        support_label="missing_context",
                        support_evidence=None,
                        verification_payload={"reason": "citation_index_not_found"},
                    )
                )
                continue

            found_count += 1
            supported, support_evidence, payload = self._check_basic_support(
                claim_text=claim_text,
                citation_row=citation_row,
            )
            if supported:
                supported_count += 1
            verifications.append(
                CitationVerification(
                    citation_marker=marker,
                    citation_index=citation_index,
                    claim_text=claim_text,
                    citation_found=True,
                    is_supported=supported,
                    support_label="supported" if supported else "unsupported",
                    support_evidence=support_evidence,
                    verification_payload=payload,
                )
            )

        total_count = len(references)
        citation_presence_rate = found_count / total_count if total_count else 0.0
        basic_support_rate = supported_count / found_count if found_count else 0.0
        logger.info(
            "Benchmark citation evaluated references=%s found=%s supported=%s presence=%.4f support=%.4f",
            total_count,
            found_count,
            supported_count,
            citation_presence_rate,
            basic_support_rate,
        )
        return CitationEvaluation(
            citation_presence_rate=citation_presence_rate,
            basic_support_rate=basic_support_rate,
            evaluator_version=evaluator_version,
            total_citation_count=total_count,
            found_citation_count=found_count,
            supported_citation_count=supported_count,
            verifications=verifications,
        )

    @staticmethod
    def _extract_answer_text(answer_payload: dict[str, Any] | None) -> str:
        if not isinstance(answer_payload, dict):
            return ""
        answer = answer_payload.get("output")
        if not isinstance(answer, str):
            return ""
        return answer.strip()

    @staticmethod
    def _extract_references(answer_text: str) -> list[tuple[int, str]]:
        if not answer_text:
            return []
        references: list[tuple[int, str]] = []
        for sentence in _SENTENCE_SPLIT_PATTERN.split(answer_text):
            chunk = sentence.strip()
            if not chunk:
                continue
            matches = list(_CITATION_PATTERN.finditer(chunk))
            if not matches:
                continue
            claim_text = _CITATION_PATTERN.sub("", chunk)
            claim_text = " ".join(claim_text.split())
            for match in matches:
                references.append((int(match.group(1)), claim_text))
        return references

    @staticmethod
    def _build_citation_map(citations: list[dict[str, Any]] | None) -> dict[int, dict[str, Any]]:
        if not isinstance(citations, list):
            return {}
        out: dict[int, dict[str, Any]] = {}
        for row in citations:
            if not isinstance(row, dict):
                continue
            index = row.get("citation_index")
            if not isinstance(index, int) or index < 1:
                continue
            out[index] = row
        return out

    def _check_basic_support(
        self,
        *,
        claim_text: str,
        citation_row: dict[str, Any],
    ) -> tuple[bool, str | None, dict[str, Any]]:
        claim_tokens = self._tokenize(claim_text)
        context_text = " ".join(
            str(citation_row.get(key, "")).strip() for key in ("title", "source", "content") if citation_row.get(key)
        )
        context_tokens = self._tokenize(context_text)
        overlap = sorted(claim_tokens & context_tokens)
        threshold = 1 if len(claim_tokens) <= 3 else 2
        is_supported = bool(claim_tokens) and len(overlap) >= threshold
        support_evidence = ", ".join(overlap[:8]) if overlap else None
        return (
            is_supported,
            support_evidence,
            {
                "overlap_tokens": overlap[:20],
                "overlap_count": len(overlap),
                "claim_token_count": len(claim_tokens),
                "context_token_count": len(context_tokens),
                "support_threshold": threshold,
            },
        )

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        if not text:
            return set()
        tokens = {token for token in _TOKEN_PATTERN.findall(text.lower()) if token not in _STOPWORDS}
        return tokens
