from __future__ import annotations

import logging
from typing import Any

from schemas import (
    RuntimeAgentRunAsyncCancelResponse,
    RuntimeAgentRunAsyncStartResponse,
    RuntimeAgentRunAsyncStatusResponse,
    RuntimeAgentRunResponse,
)

logger = logging.getLogger(__name__)


def run(
    query: str,
    *,
    vector_store: Any,
    model: Any,
    config: dict[str, Any] | None = None,
) -> RuntimeAgentRunResponse:
    logger.info(
        "SDK sync run requested query_len=%s vector_store_type=%s model_type=%s has_config=%s",
        len(query),
        type(vector_store).__name__,
        type(model).__name__,
        config is not None,
    )
    raise NotImplementedError("SDK sync runtime is not implemented yet.")


def run_async(
    query: str,
    *,
    vector_store: Any,
    model: Any,
    config: dict[str, Any] | None = None,
) -> RuntimeAgentRunAsyncStartResponse:
    logger.info(
        "SDK async run requested query_len=%s vector_store_type=%s model_type=%s has_config=%s",
        len(query),
        type(vector_store).__name__,
        type(model).__name__,
        config is not None,
    )
    raise NotImplementedError("SDK async runtime is not implemented yet.")


def get_run_status(job_id: str) -> RuntimeAgentRunAsyncStatusResponse:
    logger.info("SDK async status requested job_id=%s", job_id)
    raise NotImplementedError("SDK async status is not implemented yet.")


def cancel_run(job_id: str) -> RuntimeAgentRunAsyncCancelResponse:
    logger.info("SDK async cancel requested job_id=%s", job_id)
    raise NotImplementedError("SDK async cancel is not implemented yet.")
