from __future__ import annotations

import logging
from typing import Any

from agent_search.runtime.jobs import (
    AgentRunJobStatus,
    cancel_agent_run_job as runtime_cancel_agent_run_job,
    get_agent_run_job as runtime_get_agent_run_job,
    start_agent_run_job as runtime_start_agent_run_job,
)
from schemas import RuntimeAgentRunRequest

logger = logging.getLogger(__name__)


def start_agent_run_job(
    payload: RuntimeAgentRunRequest,
    *,
    model: Any | None = None,
    vector_store: Any | None = None,
) -> AgentRunJobStatus:
    logger.info(
        "Agent jobs service wrapper delegating start to runtime jobs query_len=%s thread_id=%s has_model=%s has_vector_store=%s",
        len(payload.query),
        payload.thread_id,
        model is not None,
        vector_store is not None,
    )
    status = runtime_start_agent_run_job(payload, model=model, vector_store=vector_store)
    logger.info(
        "Agent jobs service wrapper start delegated job_id=%s run_id=%s thread_id=%s status=%s",
        status.job_id,
        status.run_id,
        status.thread_id,
        status.status,
    )
    return status


def get_agent_run_job(job_id: str) -> AgentRunJobStatus | None:
    logger.info("Agent jobs service wrapper delegating get job_id=%s", job_id)
    status = runtime_get_agent_run_job(job_id)
    logger.info(
        "Agent jobs service wrapper get delegated job_id=%s found=%s",
        job_id,
        status is not None,
    )
    return status


def cancel_agent_run_job(job_id: str) -> bool:
    logger.info("Agent jobs service wrapper delegating cancel job_id=%s", job_id)
    cancelled = runtime_cancel_agent_run_job(job_id)
    logger.info(
        "Agent jobs service wrapper cancel delegated job_id=%s cancelled=%s",
        job_id,
        cancelled,
    )
    return cancelled
