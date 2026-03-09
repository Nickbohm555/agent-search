from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from services.document_validation_service import RetrievedDocument

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RerankerConfig:
    enabled: bool = True
    top_n: int | None = None
    model_name: str = "ms-marco-MiniLM-L-12-v2"
    cache_dir: str | None = None


@dataclass(frozen=True)
class RerankedDocumentScore:
    document: RetrievedDocument
    score: float
    original_rank: int
    reranked_rank: int


def build_reranker_config_from_env() -> RerankerConfig:
    enabled_raw = os.getenv("RERANK_ENABLED", "true").strip().casefold()
    enabled = enabled_raw not in {"0", "false", "no", "off"}
    top_n_raw = os.getenv("RERANK_TOP_N")
    top_n = int(top_n_raw) if top_n_raw not in (None, "") else None
    if top_n is not None and top_n <= 0:
        top_n = None

    model_name = os.getenv("RERANK_MODEL_NAME", "ms-marco-MiniLM-L-12-v2").strip()
    if not model_name:
        model_name = "ms-marco-MiniLM-L-12-v2"
    cache_dir = os.getenv("RERANK_CACHE_DIR")
    normalized_cache_dir = cache_dir.strip() if cache_dir and cache_dir.strip() else None

    return RerankerConfig(
        enabled=enabled,
        top_n=top_n,
        model_name=model_name,
        cache_dir=normalized_cache_dir,
    )


@lru_cache(maxsize=8)
def _build_ranker(model_name: str, cache_dir: str | None) -> Any:
    from flashrank import Ranker

    kwargs: dict[str, Any] = {"model_name": model_name}
    if cache_dir is not None:
        kwargs["cache_dir"] = cache_dir
    return Ranker(**kwargs)


def _truncate_documents(*, documents: list[RetrievedDocument], top_n: int | None) -> list[RetrievedDocument]:
    if top_n is None:
        return list(documents)
    return list(documents[:top_n])


def _fallback_scores(*, documents: list[RetrievedDocument], top_n: int | None) -> list[RerankedDocumentScore]:
    selected = _truncate_documents(documents=documents, top_n=top_n)
    output: list[RerankedDocumentScore] = []
    for reranked_rank, document in enumerate(selected, start=1):
        output.append(
            RerankedDocumentScore(
                document=RetrievedDocument(
                    rank=reranked_rank,
                    title=document.title,
                    source=document.source,
                    content=document.content,
                ),
                score=None,
                original_rank=document.rank,
                reranked_rank=reranked_rank,
            )
        )
    return output


def _build_passage_text(document: RetrievedDocument) -> str:
    return "\n".join(
        part
        for part in [
            f"title: {document.title}".strip(),
            f"source: {document.source}".strip(),
            f"content: {document.content}".strip(),
        ]
        if part
    ).strip()


def rerank_documents(
    *,
    query: str,
    documents: list[RetrievedDocument],
    config: RerankerConfig,
) -> list[RerankedDocumentScore]:
    if not documents:
        return []

    if not config.enabled:
        logger.info("Reranker disabled via config; using deterministic fallback order")
        return _fallback_scores(documents=documents, top_n=config.top_n)

    try:
        from flashrank import RerankRequest
    except Exception:
        logger.exception("Flashrank import failed; using deterministic fallback order")
        return _fallback_scores(documents=documents, top_n=config.top_n)

    try:
        ranker = _build_ranker(config.model_name, config.cache_dir)
        passages: list[dict[str, str]] = []
        by_id: dict[str, RetrievedDocument] = {}
        for index, document in enumerate(documents):
            doc_id = str(index)
            by_id[doc_id] = document
            passages.append({"id": doc_id, "text": _build_passage_text(document)})
        request = RerankRequest(query=query, passages=passages)
        ranked = ranker.rerank(request) or []
    except Exception:
        logger.exception(
            "Flashrank rerank failed model_name=%s top_n=%s; using deterministic fallback order",
            config.model_name,
            config.top_n,
        )
        return _fallback_scores(documents=documents, top_n=config.top_n)

    ordered_docs: list[tuple[RetrievedDocument, float | None]] = []
    for row in ranked:
        if not isinstance(row, dict):
            continue
        doc_id = str(row.get("id", ""))
        document = by_id.get(doc_id)
        if document is None:
            continue
        score_value = row.get("score")
        score = float(score_value) if isinstance(score_value, (int, float)) else None
        ordered_docs.append((document, score))

    if not ordered_docs:
        logger.warning("Flashrank returned no mappable results; using deterministic fallback order")
        return _fallback_scores(documents=documents, top_n=config.top_n)

    seen_doc_ranks: set[int] = set()
    for document, _ in ordered_docs:
        seen_doc_ranks.add(document.rank)
    for document in documents:
        if document.rank in seen_doc_ranks:
            continue
        ordered_docs.append((document, None))

    selected_docs = ordered_docs if config.top_n is None else ordered_docs[: config.top_n]
    output: list[RerankedDocumentScore] = []
    for reranked_rank, (document, score) in enumerate(selected_docs, start=1):
        output.append(
            RerankedDocumentScore(
                document=RetrievedDocument(
                    rank=reranked_rank,
                    title=document.title,
                    source=document.source,
                    content=document.content,
                ),
                score=score,
                original_rank=document.rank,
                reranked_rank=reranked_rank,
            )
        )
    return output
