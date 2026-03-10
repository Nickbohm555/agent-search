from __future__ import annotations

import logging
from typing import Any

from agent_search import public_api as sdk_public_api
from schemas import (
    RuntimeAgentRunAsyncCancelResponse,
    RuntimeAgentRunAsyncStartResponse,
    RuntimeAgentRunAsyncStatusResponse,
    RuntimeAgentRunResponse,
)

logger = logging.getLogger(__name__)


class BenchmarkExecutionAdapter:
    """Adapter that isolates benchmark execution from runtime internals.

    Benchmark runners should call this adapter instead of importing legacy service
    internals directly. The adapter only delegates to the SDK public API.
    """

    def run_sync(
        self,
        query: str,
        *,
        vector_store: Any,
        model: Any,
        config: dict[str, Any] | None = None,
    ) -> RuntimeAgentRunResponse:
        logger.info(
            "Benchmark execution adapter sync run query_len=%s has_config=%s",
            len(query),
            config is not None,
        )
        response = sdk_public_api.run(query, vector_store=vector_store, model=model, config=config)
        logger.info(
            "Benchmark execution adapter sync run completed sub_qa_count=%s output_len=%s",
            len(response.sub_qa),
            len(response.output),
        )
        return response

    def run_async(
        self,
        query: str,
        *,
        vector_store: Any,
        model: Any,
        config: dict[str, Any] | None = None,
    ) -> RuntimeAgentRunAsyncStartResponse:
        logger.info(
            "Benchmark execution adapter async run requested query_len=%s has_config=%s",
            len(query),
            config is not None,
        )
        response = sdk_public_api.run_async(query, vector_store=vector_store, model=model, config=config)
        logger.info(
            "Benchmark execution adapter async run queued job_id=%s run_id=%s status=%s",
            response.job_id,
            response.run_id,
            response.status,
        )
        return response

    def get_run_status(self, job_id: str) -> RuntimeAgentRunAsyncStatusResponse:
        logger.info("Benchmark execution adapter status requested job_id=%s", job_id)
        response = sdk_public_api.get_run_status(job_id)
        logger.info(
            "Benchmark execution adapter status resolved job_id=%s status=%s stage=%s",
            response.job_id,
            response.status,
            response.stage,
        )
        return response

    def cancel_run(self, job_id: str) -> RuntimeAgentRunAsyncCancelResponse:
        logger.info("Benchmark execution adapter cancel requested job_id=%s", job_id)
        response = sdk_public_api.cancel_run(job_id)
        logger.info("Benchmark execution adapter cancel accepted job_id=%s status=%s", job_id, response.status)
        return response
