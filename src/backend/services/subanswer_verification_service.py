from __future__ import annotations

import re
from dataclasses import dataclass

from services.document_validation_service import parse_retrieved_documents

_NO_EVIDENCE_PATTERNS = (
    "no relevant evidence",
    "insufficient evidence",
    "not enough evidence",
    "unable to determine",
    "cannot determine",
)
_TOKEN_PATTERN = re.compile(r"[a-z0-9]{3,}")
_MIN_EVIDENCE_TOKENS = 2
_STOPWORDS = {
    "about",
    "after",
    "also",
    "because",
    "between",
    "could",
    "from",
    "have",
    "into",
    "more",
    "most",
    "other",
    "over",
    "such",
    "than",
    "that",
    "their",
    "there",
    "these",
    "they",
    "this",
    "those",
    "very",
    "what",
    "when",
    "where",
    "which",
    "with",
    "would",
}


@dataclass(frozen=True)
class SubanswerVerificationResult:
    answerable: bool
    reason: str


def _extract_tokens(text: str) -> set[str]:
    tokens = {token for token in _TOKEN_PATTERN.findall(text.lower())}
    return {token for token in tokens if token not in _STOPWORDS}


def verify_subanswer(
    *,
    sub_question: str,
    sub_answer: str,
    reranked_retrieved_output: str,
) -> SubanswerVerificationResult:
    _ = sub_question  # Reserved for future stricter checks.

    answer_text = (sub_answer or "").strip()
    if not answer_text:
        return SubanswerVerificationResult(answerable=False, reason="empty_subanswer")

    lowered_answer = answer_text.lower()
    for pattern in _NO_EVIDENCE_PATTERNS:
        if pattern in lowered_answer:
            return SubanswerVerificationResult(answerable=False, reason="subanswer_reports_insufficient_evidence")

    documents = parse_retrieved_documents(reranked_retrieved_output)
    if not documents:
        return SubanswerVerificationResult(answerable=False, reason="no_parseable_reranked_documents")

    evidence_tokens = _extract_tokens(
        " ".join(f"{doc.title} {doc.content}" for doc in documents)
    )
    answer_tokens = _extract_tokens(answer_text)
    overlapping_tokens = answer_tokens.intersection(evidence_tokens)
    if len(overlapping_tokens) < _MIN_EVIDENCE_TOKENS:
        return SubanswerVerificationResult(answerable=False, reason="insufficient_evidence_overlap")

    return SubanswerVerificationResult(answerable=True, reason="grounded_in_reranked_documents")
