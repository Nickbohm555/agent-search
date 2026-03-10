from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping

logger = logging.getLogger(__name__)

_RERANK_PROVIDERS = {"auto", "openai"}


def _read_positive_int(*, value: Any, default: int, field_name: str) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        logger.warning(
            "RuntimeConfig invalid int override; using default field=%s value=%s default=%s",
            field_name,
            value,
            default,
        )
        return default
    if parsed <= 0:
        logger.warning(
            "RuntimeConfig non-positive int override; using default field=%s value=%s default=%s",
            field_name,
            parsed,
            default,
        )
        return default
    return parsed


def _read_optional_float(*, value: Any, default: float | None, field_name: str) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        logger.warning(
            "RuntimeConfig invalid float override; using default field=%s value=%s default=%s",
            field_name,
            value,
            default,
        )
        return default


def _read_bool(*, value: Any, default: bool, field_name: str) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().casefold()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    logger.warning(
        "RuntimeConfig invalid bool override; using default field=%s value=%s default=%s",
        field_name,
        value,
        default,
    )
    return default


@dataclass(frozen=True)
class RuntimeTimeoutConfig:
    vector_store_acquisition_timeout_s: int = 20
    initial_search_timeout_s: int = 20
    decomposition_llm_timeout_s: int = 60
    document_validation_timeout_s: int = 20
    rerank_timeout_s: int = 1
    subanswer_generation_timeout_s: int = 60
    subanswer_verification_timeout_s: int = 30
    subquestion_pipeline_total_timeout_s: int = 120
    initial_answer_timeout_s: int = 60
    refinement_decision_timeout_s: int = 30
    refinement_decomposition_timeout_s: int = 60
    refinement_retrieval_timeout_s: int = 30
    refinement_pipeline_total_timeout_s: int = 120
    refined_answer_timeout_s: int = 60

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> RuntimeTimeoutConfig:
        values = dict(data or {})
        return cls(
            vector_store_acquisition_timeout_s=_read_positive_int(
                value=values.get("vector_store_acquisition_timeout_s"),
                default=20,
                field_name="timeout.vector_store_acquisition_timeout_s",
            ),
            initial_search_timeout_s=_read_positive_int(
                value=values.get("initial_search_timeout_s"),
                default=20,
                field_name="timeout.initial_search_timeout_s",
            ),
            decomposition_llm_timeout_s=_read_positive_int(
                value=values.get("decomposition_llm_timeout_s"),
                default=60,
                field_name="timeout.decomposition_llm_timeout_s",
            ),
            document_validation_timeout_s=_read_positive_int(
                value=values.get("document_validation_timeout_s"),
                default=20,
                field_name="timeout.document_validation_timeout_s",
            ),
            rerank_timeout_s=_read_positive_int(
                value=values.get("rerank_timeout_s"),
                default=1,
                field_name="timeout.rerank_timeout_s",
            ),
            subanswer_generation_timeout_s=_read_positive_int(
                value=values.get("subanswer_generation_timeout_s"),
                default=60,
                field_name="timeout.subanswer_generation_timeout_s",
            ),
            subanswer_verification_timeout_s=_read_positive_int(
                value=values.get("subanswer_verification_timeout_s"),
                default=30,
                field_name="timeout.subanswer_verification_timeout_s",
            ),
            subquestion_pipeline_total_timeout_s=_read_positive_int(
                value=values.get("subquestion_pipeline_total_timeout_s"),
                default=120,
                field_name="timeout.subquestion_pipeline_total_timeout_s",
            ),
            initial_answer_timeout_s=_read_positive_int(
                value=values.get("initial_answer_timeout_s"),
                default=60,
                field_name="timeout.initial_answer_timeout_s",
            ),
            refinement_decision_timeout_s=_read_positive_int(
                value=values.get("refinement_decision_timeout_s"),
                default=30,
                field_name="timeout.refinement_decision_timeout_s",
            ),
            refinement_decomposition_timeout_s=_read_positive_int(
                value=values.get("refinement_decomposition_timeout_s"),
                default=60,
                field_name="timeout.refinement_decomposition_timeout_s",
            ),
            refinement_retrieval_timeout_s=_read_positive_int(
                value=values.get("refinement_retrieval_timeout_s"),
                default=30,
                field_name="timeout.refinement_retrieval_timeout_s",
            ),
            refinement_pipeline_total_timeout_s=_read_positive_int(
                value=values.get("refinement_pipeline_total_timeout_s"),
                default=120,
                field_name="timeout.refinement_pipeline_total_timeout_s",
            ),
            refined_answer_timeout_s=_read_positive_int(
                value=values.get("refined_answer_timeout_s"),
                default=60,
                field_name="timeout.refined_answer_timeout_s",
            ),
        )


@dataclass(frozen=True)
class RuntimeRetrievalConfig:
    initial_search_context_k: int = 5
    initial_search_context_score_threshold: float | None = None
    search_node_k_fetch: int = 10
    search_node_score_threshold: float | None = 0.0
    search_node_merged_cap: int = 30
    refinement_retrieval_k: int = 10

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> RuntimeRetrievalConfig:
        values = dict(data or {})
        return cls(
            initial_search_context_k=_read_positive_int(
                value=values.get("initial_search_context_k"),
                default=5,
                field_name="retrieval.initial_search_context_k",
            ),
            initial_search_context_score_threshold=_read_optional_float(
                value=values.get("initial_search_context_score_threshold"),
                default=None,
                field_name="retrieval.initial_search_context_score_threshold",
            ),
            search_node_k_fetch=_read_positive_int(
                value=values.get("search_node_k_fetch"),
                default=10,
                field_name="retrieval.search_node_k_fetch",
            ),
            search_node_score_threshold=_read_optional_float(
                value=values.get("search_node_score_threshold"),
                default=0.0,
                field_name="retrieval.search_node_score_threshold",
            ),
            search_node_merged_cap=_read_positive_int(
                value=values.get("search_node_merged_cap"),
                default=30,
                field_name="retrieval.search_node_merged_cap",
            ),
            refinement_retrieval_k=_read_positive_int(
                value=values.get("refinement_retrieval_k"),
                default=10,
                field_name="retrieval.refinement_retrieval_k",
            ),
        )


@dataclass(frozen=True)
class RuntimeRerankConfig:
    enabled: bool = True
    top_n: int | None = None
    provider: str = "openai"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> RuntimeRerankConfig:
        values = dict(data or {})
        top_n_raw = values.get("top_n")
        top_n: int | None = None
        if top_n_raw not in (None, ""):
            try:
                parsed_top_n = int(top_n_raw)
                if parsed_top_n > 0:
                    top_n = parsed_top_n
                else:
                    logger.warning(
                        "RuntimeConfig non-positive int override; disabling top_n field=rerank.top_n value=%s",
                        parsed_top_n,
                    )
            except (TypeError, ValueError):
                logger.warning(
                    "RuntimeConfig invalid int override; disabling top_n field=rerank.top_n value=%s",
                    top_n_raw,
                )

        provider_raw = str(values.get("provider", "openai")).strip().lower()
        provider = provider_raw or "openai"
        if provider not in _RERANK_PROVIDERS:
            logger.warning(
                "RuntimeConfig invalid rerank provider; using default value=%s default=%s",
                provider,
                "openai",
            )
            provider = "openai"

        return cls(
            enabled=_read_bool(value=values.get("enabled"), default=True, field_name="rerank.enabled"),
            top_n=top_n,
            provider=provider,
        )


@dataclass(frozen=True)
class RuntimeConfig:
    timeout: RuntimeTimeoutConfig = RuntimeTimeoutConfig()
    retrieval: RuntimeRetrievalConfig = RuntimeRetrievalConfig()
    rerank: RuntimeRerankConfig = RuntimeRerankConfig()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any] | None = None) -> RuntimeConfig:
        values = dict(data or {})
        timeout_data = values.get("timeout")
        retrieval_data = values.get("retrieval")
        rerank_data = values.get("rerank")

        if timeout_data is not None and not isinstance(timeout_data, Mapping):
            logger.warning("RuntimeConfig timeout section must be a mapping; using defaults")
            timeout_data = None
        if retrieval_data is not None and not isinstance(retrieval_data, Mapping):
            logger.warning("RuntimeConfig retrieval section must be a mapping; using defaults")
            retrieval_data = None
        if rerank_data is not None and not isinstance(rerank_data, Mapping):
            logger.warning("RuntimeConfig rerank section must be a mapping; using defaults")
            rerank_data = None

        config = cls(
            timeout=RuntimeTimeoutConfig.from_dict(timeout_data),
            retrieval=RuntimeRetrievalConfig.from_dict(retrieval_data),
            rerank=RuntimeRerankConfig.from_dict(rerank_data),
        )
        logger.info(
            "RuntimeConfig resolved timeout_rerank_s=%s retrieval_k=%s rerank_enabled=%s rerank_provider=%s",
            config.timeout.rerank_timeout_s,
            config.retrieval.search_node_k_fetch,
            config.rerank.enabled,
            config.rerank.provider,
        )
        return config
