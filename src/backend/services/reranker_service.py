from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from services.document_validation_service import RetrievedDocument

logger = logging.getLogger(__name__)
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
_OPENAI_JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", flags=re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class RerankerConfig:
    enabled: bool = True
    top_n: int | None = None
    provider: str = "auto"
    model_name: str = "ms-marco-MiniLM-L-12-v2"
    cache_dir: str | None = None
    openai_model_name: str = "gpt-4.1-mini"
    openai_temperature: float = 0.0


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

    provider = os.getenv("RERANK_PROVIDER", "openai").strip().lower() or "openai"
    model_name = os.getenv("RERANK_MODEL_NAME", "ms-marco-MiniLM-L-12-v2").strip()
    if not model_name:
        model_name = "ms-marco-MiniLM-L-12-v2"
    cache_dir = os.getenv("RERANK_CACHE_DIR")
    normalized_cache_dir = cache_dir.strip() if cache_dir and cache_dir.strip() else None
    openai_model_name = os.getenv("RERANK_OPENAI_MODEL_NAME", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
    openai_temperature_raw = os.getenv("RERANK_OPENAI_TEMPERATURE", "0").strip() or "0"
    try:
        openai_temperature = float(openai_temperature_raw)
    except ValueError:
        logger.warning(
            "Invalid rerank OpenAI temperature; using default value=%s default=0",
            openai_temperature_raw,
        )
        openai_temperature = 0.0

    return RerankerConfig(
        enabled=enabled,
        top_n=top_n,
        provider=provider,
        model_name=model_name,
        cache_dir=normalized_cache_dir,
        openai_model_name=openai_model_name,
        openai_temperature=openai_temperature,
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


def _resolve_provider_attempt_order(provider: str) -> list[str]:
    normalized = (provider or "").strip().lower()
    if normalized in {"", "auto"}:
        return ["openai", "flashrank"]
    if normalized == "openai":
        return ["openai", "flashrank"]
    if normalized == "flashrank":
        return ["flashrank"]
    logger.warning("Unknown rerank provider=%s; defaulting to auto", provider)
    return ["openai", "flashrank"]


def _extract_json_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return ""
    match = _OPENAI_JSON_BLOCK_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return text


def _rerank_with_openai(
    *,
    query: str,
    documents: list[RetrievedDocument],
    config: RerankerConfig,
) -> list[tuple[RetrievedDocument, float | None]] | None:
    if not _OPENAI_API_KEY:
        logger.info("OpenAI rerank unavailable; OPENAI_API_KEY missing")
        return None

    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=config.openai_model_name,
        temperature=config.openai_temperature,
    )
    payload = [
        {
            "id": str(index),
            "title": document.title,
            "source": document.source,
            "content": document.content,
        }
        for index, document in enumerate(documents)
    ]
    prompt = (
        "You are a retrieval reranker.\n"
        "Given a query and a list of passages, return a JSON array sorted from most relevant to least relevant.\n"
        'Each item must be {"id":"<original_id>","score":<0_to_1_float>}.\n'
        "Rules:\n"
        "- Keep only ids from the input.\n"
        "- Do not include duplicate ids.\n"
        "- Return strict JSON only.\n\n"
        f"Query:\n{query}\n\n"
        f"Passages:\n{json.dumps(payload, ensure_ascii=True)}"
    )
    response = llm.invoke(prompt)
    response_text = response.content if hasattr(response, "content") else ""
    parsed_text = _extract_json_text(str(response_text))
    parsed = json.loads(parsed_text)
    if not isinstance(parsed, list):
        raise ValueError("OpenAI rerank response must be a JSON list")

    by_id: dict[str, RetrievedDocument] = {
        str(index): document for index, document in enumerate(documents)
    }
    ordered_docs: list[tuple[RetrievedDocument, float | None]] = []
    seen_ids: set[str] = set()
    for row in parsed:
        if not isinstance(row, dict):
            continue
        doc_id = str(row.get("id", ""))
        if not doc_id or doc_id in seen_ids:
            continue
        document = by_id.get(doc_id)
        if document is None:
            continue
        score_value = row.get("score")
        score = float(score_value) if isinstance(score_value, (int, float)) else None
        ordered_docs.append((document, score))
        seen_ids.add(doc_id)
    return ordered_docs


def _rerank_with_flashrank(
    *,
    query: str,
    documents: list[RetrievedDocument],
    config: RerankerConfig,
) -> list[tuple[RetrievedDocument, float | None]] | None:
    try:
        from flashrank import RerankRequest
    except Exception:
        logger.exception("Flashrank import failed")
        return None

    ranker = _build_ranker(config.model_name, config.cache_dir)
    passages: list[dict[str, str]] = []
    by_id: dict[str, RetrievedDocument] = {}
    for index, document in enumerate(documents):
        doc_id = str(index)
        by_id[doc_id] = document
        passages.append({"id": doc_id, "text": _build_passage_text(document)})
    request = RerankRequest(query=query, passages=passages)
    ranked = ranker.rerank(request) or []

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
    return ordered_docs


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

    ordered_docs: list[tuple[RetrievedDocument, float | None]] = []
    for provider in _resolve_provider_attempt_order(config.provider):
        try:
            if provider == "openai":
                ordered_docs = (
                    _rerank_with_openai(query=query, documents=documents, config=config) or []
                )
            elif provider == "flashrank":
                ordered_docs = (
                    _rerank_with_flashrank(query=query, documents=documents, config=config) or []
                )
        except Exception:
            logger.exception(
                "Reranker provider failed provider=%s model_name=%s top_n=%s",
                provider,
                config.model_name,
                config.top_n,
            )
            ordered_docs = []
        if ordered_docs:
            break

    if not ordered_docs:
        logger.warning("Reranker returned no mappable results; using deterministic fallback order")
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
