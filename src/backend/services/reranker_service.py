from __future__ import annotations

import os
import re
from dataclasses import dataclass

from services.document_validation_service import RetrievedDocument

_WORD_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class RerankerConfig:
    top_n: int | None = None
    title_weight: float = 1.3
    content_weight: float = 1.0
    source_weight: float = 0.3
    original_rank_bias: float = 0.05


@dataclass(frozen=True)
class RerankedDocumentScore:
    document: RetrievedDocument
    score: float
    original_rank: int
    reranked_rank: int


def build_reranker_config_from_env() -> RerankerConfig:
    top_n_raw = os.getenv("RERANK_TOP_N")
    top_n = int(top_n_raw) if top_n_raw not in (None, "") else None
    if top_n is not None and top_n <= 0:
        top_n = None

    return RerankerConfig(
        top_n=top_n,
        title_weight=float(os.getenv("RERANK_TITLE_WEIGHT", "1.3")),
        content_weight=float(os.getenv("RERANK_CONTENT_WEIGHT", "1.0")),
        source_weight=float(os.getenv("RERANK_SOURCE_WEIGHT", "0.3")),
        original_rank_bias=float(os.getenv("RERANK_ORIGINAL_RANK_BIAS", "0.05")),
    )


def _tokenize(value: str) -> set[str]:
    return {token for token in _WORD_PATTERN.findall(value.lower()) if token}


def _overlap_ratio(query_tokens: set[str], text: str) -> float:
    if not query_tokens:
        return 0.0
    text_tokens = _tokenize(text)
    if not text_tokens:
        return 0.0
    return len(query_tokens & text_tokens) / len(query_tokens)


def _score_document(query: str, document: RetrievedDocument, config: RerankerConfig) -> float:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return 0.0

    lexical_score = (
        config.title_weight * _overlap_ratio(query_tokens, document.title)
        + config.content_weight * _overlap_ratio(query_tokens, document.content)
        + config.source_weight * _overlap_ratio(query_tokens, document.source)
    )
    rank_boost = config.original_rank_bias / max(document.rank, 1)
    return lexical_score + rank_boost


def rerank_documents(
    *,
    query: str,
    documents: list[RetrievedDocument],
    config: RerankerConfig,
) -> list[RerankedDocumentScore]:
    if not documents:
        return []

    scored: list[tuple[RetrievedDocument, float]] = [
        (doc, _score_document(query=query, document=doc, config=config))
        for doc in documents
    ]
    scored.sort(key=lambda item: (-item[1], item[0].rank))

    if config.top_n is not None:
        scored = scored[: config.top_n]

    reranked: list[RerankedDocumentScore] = []
    for idx, (doc, score) in enumerate(scored, start=1):
        reranked.append(
            RerankedDocumentScore(
                document=RetrievedDocument(
                    rank=idx,
                    title=doc.title,
                    source=doc.source,
                    content=doc.content,
                ),
                score=score,
                original_rank=doc.rank,
                reranked_rank=idx,
            )
        )
    return reranked
