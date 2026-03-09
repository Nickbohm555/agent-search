from __future__ import annotations

import logging
import time
from typing import Any, cast

from schemas import (
    RuntimeAgentRunRequest,
    RuntimeAgentRunAsyncCancelResponse,
    RuntimeAgentRunAsyncStartResponse,
    RuntimeAgentRunAsyncStatusResponse,
    RuntimeAgentRunResponse,
)
from services.agent_jobs import cancel_agent_run_job, get_agent_run_job, start_agent_run_job
from services.agent_service import run_runtime_agent

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
    if model is None:
        logger.error("SDK sync run rejected missing model")
        raise TypeError("model is required and cannot be None")
    if vector_store is None:
        logger.error("SDK sync run rejected missing vector_store")
        raise TypeError("vector_store is required and cannot be None")

    response = run_runtime_agent(
        RuntimeAgentRunRequest(query=query),
        db=cast(Any, None),
        model=model,
        vector_store=vector_store,
    )
    logger.info(
        "SDK sync run completed sub_qa_count=%s output_len=%s",
        len(response.sub_qa),
        len(response.output),
    )
    return response


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
    if model is None:
        logger.error("SDK async run rejected missing model")
        raise TypeError("model is required and cannot be None")
    if vector_store is None:
        logger.error("SDK async run rejected missing vector_store")
        raise TypeError("vector_store is required and cannot be None")

    # Async runtime currently resolves dependencies in service layer.
    job = start_agent_run_job(RuntimeAgentRunRequest(query=query))
    response = RuntimeAgentRunAsyncStartResponse(job_id=job.job_id, run_id=job.run_id, status=job.status)
    logger.info(
        "SDK async run queued job_id=%s run_id=%s status=%s",
        response.job_id,
        response.run_id,
        response.status,
    )
    return response


def get_run_status(job_id: str) -> RuntimeAgentRunAsyncStatusResponse:
    logger.info("SDK async status requested job_id=%s", job_id)
    job = get_agent_run_job(job_id)
    if job is None:
        logger.error("SDK async status failed job_id=%s not found", job_id)
        raise ValueError("Job not found.")

    now = time.time()
    started_at = getattr(job, "started_at", None)
    finished_at = getattr(job, "finished_at", None)
    elapsed_ms = None
    if started_at is not None:
        elapsed_ms = int(((finished_at or now) - started_at) * 1000)

    response = RuntimeAgentRunAsyncStatusResponse(
        job_id=job.job_id,
        run_id=job.run_id,
        status=job.status,
        message=job.message,
        stage=job.stage,
        stages=list(job.stages),
        decomposition_sub_questions=list(job.decomposition_sub_questions),
        sub_question_artifacts=[item.model_copy(deep=True) for item in job.sub_question_artifacts],
        sub_qa=[item.model_copy(deep=True) for item in job.sub_qa],
        output=job.output,
        result=job.result.model_copy(deep=True) if job.result is not None else None,
        error=job.error,
        cancel_requested=job.cancel_requested,
        started_at=started_at,
        finished_at=finished_at,
        elapsed_ms=elapsed_ms,
    )
    logger.info(
        "SDK async status resolved job_id=%s status=%s stage=%s elapsed_ms=%s",
        response.job_id,
        response.status,
        response.stage,
        response.elapsed_ms,
    )
    return response


def cancel_run(job_id: str) -> RuntimeAgentRunAsyncCancelResponse:
    logger.info("SDK async cancel requested job_id=%s", job_id)
    cancelled = cancel_agent_run_job(job_id)
    if not cancelled:
        logger.error("SDK async cancel failed job_id=%s not found_or_finished", job_id)
        raise ValueError("Job not found or already finished.")
    response = RuntimeAgentRunAsyncCancelResponse(status="success", message="Cancellation requested.")
    logger.info("SDK async cancel accepted job_id=%s", job_id)
    return response
