from __future__ import annotations

import logging
import os
import re
from typing import Any
from dataclasses import dataclass

from langchain_classic.retrievers.multi_query import MultiQueryRetriever
from langchain_core.callbacks.manager import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.retrievers import BaseRetriever
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

_RUNTIME_AGENT_MODEL = os.getenv("RUNTIME_AGENT_MODEL", "gpt-4.1-mini")
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()


@dataclass(frozen=True)
class QueryExpansionConfig:
    model: str
    temperature: float
    max_queries: int
    max_query_length: int


def _read_positive_int(env_key: str, default: int, *, min_value: int = 1) -> int:
    raw_value = os.getenv(env_key, "").strip()
    if not raw_value:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid query expansion config; using default env_key=%s value=%s default=%s",
            env_key,
            raw_value,
            default,
        )
        return default
    if parsed < min_value:
        logger.warning(
            "Out-of-range query expansion config; using default env_key=%s value=%s default=%s",
            env_key,
            parsed,
            default,
        )
        return default
    return parsed


def _read_float(env_key: str, default: float) -> float:
    raw_value = os.getenv(env_key, "").strip()
    if not raw_value:
        return default
    try:
        return float(raw_value)
    except ValueError:
        logger.warning(
            "Invalid query expansion float config; using default env_key=%s value=%s default=%s",
            env_key,
            raw_value,
            default,
        )
        return default


def build_query_expansion_config_from_env() -> QueryExpansionConfig:
    return QueryExpansionConfig(
        model=os.getenv("QUERY_EXPANSION_MODEL", _RUNTIME_AGENT_MODEL).strip() or _RUNTIME_AGENT_MODEL,
        temperature=_read_float("QUERY_EXPANSION_TEMPERATURE", 0.0),
        max_queries=_read_positive_int("QUERY_EXPANSION_MAX_QUERIES", 4, min_value=1),
        max_query_length=_read_positive_int("QUERY_EXPANSION_MAX_QUERY_LENGTH", 256, min_value=16),
    )


def _normalize_query(text: str, *, max_query_length: int) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip())
    if not normalized:
        return ""
    if len(normalized) > max_query_length:
        return normalized[:max_query_length].strip()
    return normalized


def _normalize_query_candidates(
    *,
    original_query: str,
    generated_queries: list[str],
    config: QueryExpansionConfig,
) -> list[str]:
    normalized_queries: list[str] = []
    seen: set[str] = set()
    candidates = [original_query, *generated_queries]
    for candidate in candidates:
        normalized = _normalize_query(candidate, max_query_length=config.max_query_length)
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        normalized_queries.append(normalized)
        seen.add(key)
        if len(normalized_queries) >= config.max_queries:
            break

    if normalized_queries:
        return normalized_queries
    fallback_query = _normalize_query(original_query, max_query_length=config.max_query_length)
    return [fallback_query] if fallback_query else []


class _NoopRetriever(BaseRetriever):
    def _get_relevant_documents(self, query: str, *, run_manager) -> list[Document]:
        _ = query, run_manager
        return []

    async def _aget_relevant_documents(self, query: str, *, run_manager) -> list[Document]:
        _ = query, run_manager
        return []


def expand_queries_for_subquestion(
    *,
    sub_question: str,
    model: BaseChatModel | None = None,
    config: QueryExpansionConfig | None = None,
    callbacks: list[Any] | None = None,
) -> list[str]:
    effective_config = config or build_query_expansion_config_from_env()
    normalized_sub_question = _normalize_query(sub_question, max_query_length=effective_config.max_query_length)
    if not normalized_sub_question:
        logger.info("Query expansion skipped; empty sub-question")
        return []

    if model is None and not _OPENAI_API_KEY:
        logger.info(
            "Query expansion fallback to original; OPENAI_API_KEY is not set sub_question=%s",
            normalized_sub_question,
        )
        return [normalized_sub_question]

    try:
        llm = model or ChatOpenAI(
            model=effective_config.model,
            temperature=effective_config.temperature,
        )
        if callbacks:
            with_config = getattr(llm, "with_config", None)
            if callable(with_config):
                llm = llm.with_config({"callbacks": callbacks})
        multi_query_retriever = MultiQueryRetriever.from_llm(
            retriever=_NoopRetriever(),
            llm=llm,
            include_original=False,
        )
        generated = multi_query_retriever.generate_queries(
            normalized_sub_question,
            run_manager=CallbackManagerForRetrieverRun.get_noop_manager(),
        )
        normalized_queries = _normalize_query_candidates(
            original_query=normalized_sub_question,
            generated_queries=generated if isinstance(generated, list) else [],
            config=effective_config,
        )
        logger.info(
            "Query expansion generated sub_question=%s generated_count=%s normalized_count=%s max_queries=%s",
            normalized_sub_question,
            len(generated) if isinstance(generated, list) else 0,
            len(normalized_queries),
            effective_config.max_queries,
        )
        return normalized_queries
    except Exception:
        logger.exception(
            "Query expansion generation failed; using fallback sub_question=%s model=%s",
            normalized_sub_question,
            effective_config.model,
        )
        return [normalized_sub_question]
