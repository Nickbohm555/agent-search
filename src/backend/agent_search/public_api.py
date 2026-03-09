from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeoutError
import logging
import time
from typing import Any

from agent_search.config import RuntimeConfig
from agent_search.errors import (
    SDKConfigurationError,
    SDKError,
    SDKModelError,
    SDKRetrievalError,
    SDKTimeoutError,
)
from agent_search.runtime.jobs import cancel_agent_run_job, get_agent_run_job, start_agent_run_job
from agent_search.runtime.runner import run_runtime_agent
from agent_search.vectorstore.protocol import assert_vector_store_compatible
from schemas import (
    RuntimeAgentRunRequest,
    RuntimeAgentRunAsyncCancelResponse,
    RuntimeAgentRunAsyncStartResponse,
    RuntimeAgentRunAsyncStatusResponse,
    RuntimeAgentRunResponse,
)

logger = logging.getLogger(__name__)


def _map_sdk_error(*, operation: str, exc: Exception) -> SDKError:
    if isinstance(exc, SDKError):
        return exc
    if isinstance(exc, (TimeoutError, FuturesTimeoutError)):
        return SDKTimeoutError(f"{operation} timed out.")

    message = str(exc).lower()
    if any(token in message for token in ("vector", "retriev", "document search", "similarity search")):
        return SDKRetrievalError(f"{operation} failed during retrieval.")
    if any(token in message for token in ("model", "llm", "openai", "completion", "chat")):
        return SDKModelError(f"{operation} failed during model execution.")
    if any(token in message for token in ("config", "invalid", "missing", "required", "argument", "job not found")):
        return SDKConfigurationError(f"{operation} failed due to invalid SDK input or configuration.")

    return SDKError(f"{operation} failed.")


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
    runtime_config = RuntimeConfig.from_dict(config)
    logger.info(
        "SDK sync runtime config resolved initial_k=%s rerank_enabled=%s rerank_provider=%s",
        runtime_config.retrieval.initial_search_context_k,
        runtime_config.rerank.enabled,
        runtime_config.rerank.provider,
    )
    if model is None:
        logger.error("SDK sync run rejected missing model")
        raise SDKConfigurationError("model is required and cannot be None")
    if vector_store is None:
        logger.error("SDK sync run rejected missing vector_store")
        raise SDKConfigurationError("vector_store is required and cannot be None")
    compatible_vector_store = assert_vector_store_compatible(vector_store)
    logger.info(
        "SDK sync run vector_store validated vector_store_type=%s",
        type(compatible_vector_store).__name__,
    )

    try:
        response = run_runtime_agent(
            RuntimeAgentRunRequest(query=query),
            model=model,
            vector_store=compatible_vector_store,
        )
    except Exception as exc:  # noqa: BLE001
        mapped = _map_sdk_error(operation="run", exc=exc)
        logger.exception(
            "SDK sync run failed mapped_error=%s original_error=%s",
            type(mapped).__name__,
            type(exc).__name__,
        )
        raise mapped from exc
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
    runtime_config = RuntimeConfig.from_dict(config)
    logger.info(
        "SDK async runtime config resolved initial_k=%s rerank_enabled=%s rerank_provider=%s",
        runtime_config.retrieval.initial_search_context_k,
        runtime_config.rerank.enabled,
        runtime_config.rerank.provider,
    )
    if model is None:
        logger.error("SDK async run rejected missing model")
        raise SDKConfigurationError("model is required and cannot be None")
    if vector_store is None:
        logger.error("SDK async run rejected missing vector_store")
        raise SDKConfigurationError("vector_store is required and cannot be None")
    compatible_vector_store = assert_vector_store_compatible(vector_store)
    logger.info(
        "SDK async run vector_store validated vector_store_type=%s",
        type(compatible_vector_store).__name__,
    )

    try:
        # Async runtime currently resolves dependencies in service layer.
        job = start_agent_run_job(
            RuntimeAgentRunRequest(query=query),
            model=model,
            vector_store=compatible_vector_store,
        )
    except Exception as exc:  # noqa: BLE001
        mapped = _map_sdk_error(operation="run_async", exc=exc)
        logger.exception(
            "SDK async run failed mapped_error=%s original_error=%s",
            type(mapped).__name__,
            type(exc).__name__,
        )
        raise mapped from exc
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
    try:
        job = get_agent_run_job(job_id)
        if job is None:
            logger.error("SDK async status failed job_id=%s not found", job_id)
            raise SDKConfigurationError("Job not found.")
    except Exception as exc:  # noqa: BLE001
        mapped = _map_sdk_error(operation="get_run_status", exc=exc)
        logger.exception(
            "SDK async status failed mapped_error=%s original_error=%s job_id=%s",
            type(mapped).__name__,
            type(exc).__name__,
            job_id,
        )
        raise mapped from exc

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
    try:
        cancelled = cancel_agent_run_job(job_id)
        if not cancelled:
            logger.error("SDK async cancel failed job_id=%s not found_or_finished", job_id)
            raise SDKConfigurationError("Job not found or already finished.")
    except Exception as exc:  # noqa: BLE001
        mapped = _map_sdk_error(operation="cancel_run", exc=exc)
        logger.exception(
            "SDK async cancel failed mapped_error=%s original_error=%s job_id=%s",
            type(mapped).__name__,
            type(exc).__name__,
            job_id,
        )
        raise mapped from exc
    response = RuntimeAgentRunAsyncCancelResponse(status="success", message="Cancellation requested.")
    logger.info("SDK async cancel accepted job_id=%s", job_id)
    return response
