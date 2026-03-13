from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
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
    model_name: str | None = None
    openai_model_name: str = "gpt-4.1-mini"
    openai_temperature: float = 0.0

    def __post_init__(self) -> None:
        if self.model_name is None:
            object.__setattr__(self, "model_name", self.openai_model_name)
        elif self.openai_model_name == "gpt-4.1-mini":
            object.__setattr__(self, "openai_model_name", self.model_name)


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
        model_name=openai_model_name,
        openai_model_name=openai_model_name,
        openai_temperature=openai_temperature,
    )


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


def _resolve_provider_attempt_order(provider: str) -> list[str]:
    normalized = (provider or "").strip().lower()
    if normalized in {"", "auto"}:
        return ["openai"]
    if normalized == "openai":
        return ["openai"]
    logger.warning("Unknown rerank provider=%s; defaulting to auto", provider)
    return ["openai"]


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
    callbacks: list[Any] | None = None,
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
    invoke_config = {"callbacks": callbacks} if callbacks else None
    response = llm.invoke(prompt, config=invoke_config) if invoke_config else llm.invoke(prompt)
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


def rerank_documents(
    *,
    query: str,
    documents: list[RetrievedDocument],
    config: RerankerConfig,
    callbacks: list[Any] | None = None,
) -> list[RerankedDocumentScore]:
    if not documents:
        return []

    if not config.enabled:
        raise ValueError("Rerank is required and cannot be disabled.")

    ordered_docs: list[tuple[RetrievedDocument, float | None]] = []
    for provider in _resolve_provider_attempt_order(config.provider):
        try:
            if provider == "openai":
                ordered_docs = (
                    _rerank_with_openai(
                        query=query,
                        documents=documents,
                        config=config,
                        callbacks=callbacks,
                    )
                    or []
                )
        except Exception:
            logger.exception(
                "Reranker provider failed provider=%s model_name=%s top_n=%s",
                provider,
                config.openai_model_name,
                config.top_n,
            )
            ordered_docs = []
        if ordered_docs:
            break

    if not ordered_docs:
        raise RuntimeError("Rerank failed to return any results.")

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
