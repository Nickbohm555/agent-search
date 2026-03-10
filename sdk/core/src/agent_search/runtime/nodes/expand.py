from __future__ import annotations

import json
import logging
from typing import Any, Callable

from langchain_core.language_models.chat_models import BaseChatModel

from schemas import ExpandNodeInput, ExpandNodeOutput
from services.query_expansion_service import (
    QueryExpansionConfig,
    build_query_expansion_config_from_env,
    expand_queries_for_subquestion,
)

logger = logging.getLogger(__name__)

_QUERY_LOG_MAX = 200
_QUERY_EXPANSION_CONFIG = build_query_expansion_config_from_env()


def _truncate_query(q: str) -> str:
    return q[: _QUERY_LOG_MAX] + "..." if len(q) > _QUERY_LOG_MAX else q


def run_expansion_node(
    *,
    node_input: ExpandNodeInput,
    model: BaseChatModel | None = None,
    config: QueryExpansionConfig | None = None,
    callbacks: list[Any] | None = None,
    default_config: QueryExpansionConfig = _QUERY_EXPANSION_CONFIG,
    expand_queries_fn: Callable[..., list[str]] = expand_queries_for_subquestion,
    truncate_query_fn: Callable[[str], str] = _truncate_query,
) -> ExpandNodeOutput:
    effective_config = config or default_config
    logger.info(
        "Expansion node start sub_question=%s max_queries=%s max_query_length=%s run_id=%s trace_id=%s correlation_id=%s",
        truncate_query_fn(node_input.sub_question),
        effective_config.max_queries,
        effective_config.max_query_length,
        node_input.run_metadata.run_id,
        node_input.run_metadata.trace_id,
        node_input.run_metadata.correlation_id,
    )
    expanded_queries = expand_queries_fn(
        sub_question=node_input.sub_question,
        model=model,
        config=effective_config,
        callbacks=callbacks,
    )
    logger.info(
        "Expansion node complete sub_question=%s expanded_query_count=%s expanded_queries=%s run_id=%s",
        truncate_query_fn(node_input.sub_question),
        len(expanded_queries),
        json.dumps(expanded_queries, ensure_ascii=True),
        node_input.run_metadata.run_id,
    )
    return ExpandNodeOutput(expanded_queries=expanded_queries)


__all__ = ["run_expansion_node"]
