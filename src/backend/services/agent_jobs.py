from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Optional

from db import DATABASE_URL
from schemas import (
    AgentRunStageMetadata,
    GraphStageSnapshot,
    RuntimeAgentRunRequest,
    RuntimeAgentRunResponse,
    SubQuestionAnswer,
)
from services.agent_service import (
    build_graph_run_metadata,
    map_graph_state_to_runtime_response,
    run_parallel_graph_runner,
)
from services.vector_store_service import (
    build_initial_search_context,
    get_vector_store,
    search_documents_for_context,
)
from utils.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

_VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")
_INITIAL_SEARCH_CONTEXT_K = int(os.getenv("INITIAL_SEARCH_CONTEXT_K", "5"))
_INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD_RAW = os.getenv("INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD")
_INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD = (
    float(_INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD_RAW)
    if _INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD_RAW not in (None, "")
    else None
)
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
    sub_qa: list[SubQuestionAnswer] = field(default_factory=list)
    output: str = ""
    result: Optional[RuntimeAgentRunResponse] = None
    error: Optional[str] = None
    cancel_requested: bool = False
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None


_JOBS: dict[str, AgentRunJobStatus] = {}


def start_agent_run_job(payload: RuntimeAgentRunRequest) -> AgentRunJobStatus:
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
    logger.info("Agent async job created job_id=%s run_id=%s", job_id, run_metadata.run_id)
    _EXECUTOR.submit(_run_agent_job, job_id, payload, run_metadata.run_id)
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
        logger.info("Agent async job cancel requested job_id=%s run_id=%s", job.job_id, job.run_id)
        return True


def _stage_from_snapshot(snapshot: GraphStageSnapshot) -> str:
    if snapshot.stage == "decompose":
        return "subquestions_ready"
    return snapshot.stage


def _run_agent_job(job_id: str, payload: RuntimeAgentRunRequest, run_id: str) -> None:
    job = get_agent_run_job(job_id)
    if job is None:
        return
    if job.cancel_requested:
        with _JOB_LOCK:
            job.status = "cancelled"
            job.message = "Cancelled before run started."
            job.finished_at = time.time()
        logger.info("Agent async job cancelled before start job_id=%s run_id=%s", job_id, run_id)
        return

    logger.info("Agent async job started job_id=%s run_id=%s query_len=%s", job_id, run_id, len(payload.query))
    with _JOB_LOCK:
        job.stage = "initializing"
        job.message = "Initializing vector store."

    try:
        vector_store = get_vector_store(
            connection=DATABASE_URL,
            collection_name=_VECTOR_COLLECTION_NAME,
            embeddings=get_embedding_model(),
        )
        logger.info(
            "Agent async job vector store ready job_id=%s run_id=%s collection_name=%s",
            job_id,
            run_id,
            _VECTOR_COLLECTION_NAME,
        )

        initial_context_docs = search_documents_for_context(
            vector_store=vector_store,
            query=payload.query,
            k=_INITIAL_SEARCH_CONTEXT_K,
            score_threshold=_INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD,
        )
        initial_search_context = build_initial_search_context(initial_context_docs)
        logger.info(
            "Agent async job initial context built job_id=%s run_id=%s docs=%s",
            job_id,
            run_id,
            len(initial_search_context),
        )

        def on_snapshot(snapshot: GraphStageSnapshot, state) -> None:  # noqa: ANN001
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
                current_job.sub_qa = [item.model_copy(deep=True) for item in snapshot.sub_qa]
                current_job.output = snapshot.output
            logger.info(
                "Agent async job snapshot job_id=%s run_id=%s stage=%s lane_index=%s lane_total=%s subquestions=%s",
                job_id,
                run_id,
                mapped_stage,
                snapshot.lane_index,
                snapshot.lane_total,
                len(snapshot.decomposition_sub_questions),
            )

        state = run_parallel_graph_runner(
            payload=payload,
            vector_store=vector_store,
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
            current_job.output = response.output
            current_job.finished_at = time.time()
        logger.info(
            "Agent async job finished job_id=%s run_id=%s status=%s sub_qa_count=%s output_len=%s",
            job_id,
            run_id,
            current_job.status,
            len(response.sub_qa),
            len(response.output),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent async job failed job_id=%s run_id=%s", job_id, run_id)
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
