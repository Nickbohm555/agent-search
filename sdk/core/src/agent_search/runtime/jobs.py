from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Optional

from agent_search.errors import SDKConfigurationError
from schemas import (
    AgentRunStageMetadata,
    GraphStageSnapshot,
    RuntimeAgentRunRequest,
    RuntimeAgentRunResponse,
    SubQuestionAnswer,
    SubQuestionArtifacts,
)
from services.agent_service import (
    build_graph_run_metadata,
    map_graph_state_to_runtime_response,
    run_parallel_graph_runner,
)

logger = logging.getLogger(__name__)

_VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")
_EXECUTOR = ThreadPoolExecutor(max_workers=4)
_JOB_LOCK = threading.Lock()


@dataclass
class AgentRunJobStatus:
    job_id: str
    run_id: str
    status: str
    message: str = ""
    stage: str = "queued"
    stages: list[AgentRunStageMetadata] = field(default_factory=list)
    decomposition_sub_questions: list[str] = field(default_factory=list)
    sub_question_artifacts: list[SubQuestionArtifacts] = field(default_factory=list)
    sub_qa: list[SubQuestionAnswer] = field(default_factory=list)
    output: str = ""
    result: Optional[RuntimeAgentRunResponse] = None
    error: Optional[str] = None
    cancel_requested: bool = False
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None


_JOBS: dict[str, AgentRunJobStatus] = {}


def start_agent_run_job(
    payload: RuntimeAgentRunRequest,
    *,
    model: Any | None = None,
    vector_store: Any | None = None,
) -> AgentRunJobStatus:
    if model is None:
        logger.error("Runtime async job rejected missing model")
        raise SDKConfigurationError("model is required and cannot be None")
    if vector_store is None:
        logger.error("Runtime async job rejected missing vector_store")
        raise SDKConfigurationError("vector_store is required and cannot be None")
    job_id = str(uuid.uuid4())
    run_metadata = build_graph_run_metadata(run_id=job_id)
    status = AgentRunJobStatus(
        job_id=job_id,
        run_id=run_metadata.run_id,
        status="running",
        message="Run queued.",
        stage="queued",
    )
    with _JOB_LOCK:
        _JOBS[job_id] = status
    logger.info(
        "Runtime async job created job_id=%s run_id=%s has_model=%s has_vector_store=%s",
        job_id,
        run_metadata.run_id,
        model is not None,
        vector_store is not None,
    )
    _EXECUTOR.submit(_run_agent_job, job_id, payload, run_metadata.run_id, model, vector_store)
    return status


def get_agent_run_job(job_id: str) -> Optional[AgentRunJobStatus]:
    with _JOB_LOCK:
        return _JOBS.get(job_id)


def cancel_agent_run_job(job_id: str) -> bool:
    with _JOB_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return False
        if job.status in {"success", "error", "cancelled"}:
            return False
        job.cancel_requested = True
        job.status = "cancelling"
        job.message = "Cancellation requested."
        logger.info("Runtime async job cancel requested job_id=%s run_id=%s", job.job_id, job.run_id)
        return True


def _stage_from_snapshot(snapshot: GraphStageSnapshot) -> str:
    if snapshot.stage == "decompose":
        return "subquestions_ready"
    return snapshot.stage


def _run_agent_job(
    job_id: str,
    payload: RuntimeAgentRunRequest,
    run_id: str,
    model: Any | None,
    vector_store: Any | None,
) -> None:
    job = get_agent_run_job(job_id)
    if job is None:
        return
    if job.cancel_requested:
        with _JOB_LOCK:
            job.status = "cancelled"
            job.message = "Cancelled before run started."
            job.finished_at = time.time()
        logger.info("Runtime async job cancelled before start job_id=%s run_id=%s", job_id, run_id)
        return

    logger.info("Runtime async job started job_id=%s run_id=%s query_len=%s", job_id, run_id, len(payload.query))
    with _JOB_LOCK:
        job.stage = "initializing"
        job.message = "Initializing vector store."

    try:
        resolved_vector_store = vector_store
        if resolved_vector_store is None:
            raise SDKConfigurationError("vector_store is required and cannot be None")
        if model is None:
            raise SDKConfigurationError("model is required and cannot be None")
        logger.info(
            "Runtime async job vector store ready source=provided job_id=%s run_id=%s",
            job_id,
            run_id,
        )

        initial_search_context: list[dict[str, Any]] = []
        logger.info(
            "Runtime async job initial context retrieval disabled; proceeding with empty context job_id=%s run_id=%s",
            job_id,
            run_id,
        )

        def on_snapshot(snapshot: GraphStageSnapshot, _state: Any) -> None:
            mapped_stage = _stage_from_snapshot(snapshot)
            stage_metadata = AgentRunStageMetadata(
                stage=mapped_stage,
                status=snapshot.status,
                sub_question=snapshot.sub_question,
                lane_index=snapshot.lane_index,
                lane_total=snapshot.lane_total,
                emitted_at=time.time(),
            )
            with _JOB_LOCK:
                current_job = _JOBS.get(job_id)
                if current_job is None:
                    return
                current_job.stage = mapped_stage
                current_job.message = f"Stage completed: {mapped_stage}"
                current_job.stages.append(stage_metadata)
                current_job.decomposition_sub_questions = list(snapshot.decomposition_sub_questions)
                current_job.sub_question_artifacts = [item.model_copy(deep=True) for item in snapshot.sub_question_artifacts]
                current_job.sub_qa = [item.model_copy(deep=True) for item in snapshot.sub_qa]
                current_job.output = snapshot.output
            logger.info(
                "Runtime async job snapshot job_id=%s run_id=%s stage=%s lane_index=%s lane_total=%s subquestions=%s",
                job_id,
                run_id,
                mapped_stage,
                snapshot.lane_index,
                snapshot.lane_total,
                len(snapshot.decomposition_sub_questions),
            )

        state = run_parallel_graph_runner(
            payload=payload,
            vector_store=resolved_vector_store,
            model=model,
            run_metadata=build_graph_run_metadata(run_id=run_id),
            initial_search_context=initial_search_context,
            snapshot_callback=on_snapshot,
        )
        response = map_graph_state_to_runtime_response(state)
        with _JOB_LOCK:
            current_job = _JOBS.get(job_id)
            if current_job is None:
                return
            if current_job.cancel_requested:
                current_job.status = "cancelled"
                current_job.message = "Cancelled."
            else:
                current_job.status = "success"
                current_job.message = "Completed."
                current_job.result = response
            current_job.sub_qa = [item.model_copy(deep=True) for item in response.sub_qa]
            current_job.decomposition_sub_questions = list(state.decomposition_sub_questions)
            current_job.sub_question_artifacts = [item.model_copy(deep=True) for item in state.sub_question_artifacts]
            current_job.output = response.output
            current_job.finished_at = time.time()
        logger.info(
            "Runtime async job finished job_id=%s run_id=%s status=%s sub_qa_count=%s output_len=%s",
            job_id,
            run_id,
            current_job.status,
            len(response.sub_qa),
            len(response.output),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Runtime async job failed job_id=%s run_id=%s", job_id, run_id)
        with _JOB_LOCK:
            current_job = _JOBS.get(job_id)
            if current_job is None:
                return
            if current_job.cancel_requested:
                current_job.status = "cancelled"
                current_job.message = "Cancelled."
                current_job.error = None
            else:
                current_job.status = "error"
                current_job.message = "Failed."
                current_job.error = str(exc)
            current_job.finished_at = time.time()
