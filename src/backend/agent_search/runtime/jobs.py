from __future__ import annotations

import inspect
import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from agent_search.errors import SDKConfigurationError
from agent_search.runtime.execution_identity import resolve_thread_identity
from agent_search.runtime.graph.execution import execute_runtime_graph
from agent_search.runtime.graph.state import RuntimeGraphContext
from agent_search.runtime.lifecycle_events import RuntimeLifecycleEvent
from agent_search.runtime.resume import (
    ResumeTransitionError,
    attach_checkpoint_metadata,
    ensure_resume_allowed,
    normalize_resume_payload,
)
from agent_search.runtime.state import to_rag_state
from db import SessionLocal
from models import RuntimeCheckpointLink
from schemas import (
    AgentRunStageMetadata,
    GraphStageSnapshot,
    RuntimeAgentRunRequest,
    RuntimeAgentRunResponse,
    SubQuestionAnswer,
    SubQuestionArtifacts,
)
from services.agent_service import build_graph_run_metadata, map_graph_state_to_runtime_response
from agent_search.runtime.runner import run_checkpointed_agent

logger = logging.getLogger(__name__)

_VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")
_EXECUTOR = ThreadPoolExecutor(max_workers=4)
_JOB_LOCK = threading.Lock()


@dataclass
class AgentRunJobStatus:
    job_id: str
    run_id: str
    thread_id: str
    status: str
    trace_id: str = ""
    query: str = ""
    request_payload: dict[str, Any] = field(default_factory=dict)
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
    interrupt_payload: Any | None = None
    checkpoint_id: str | None = None
    lifecycle_events: list[RuntimeLifecycleEvent] = field(default_factory=list)
    runtime_model: Any | None = field(default=None, repr=False)
    runtime_vector_store: Any | None = field(default=None, repr=False)
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None


_JOBS: dict[str, AgentRunJobStatus] = {}
_TERMINAL_LIFECYCLE_EVENT_TYPES = frozenset({"run.completed", "run.failed", "run.paused"})


def _call_with_supported_kwargs(func: Any, /, **kwargs: Any) -> Any:
    signature = inspect.signature(func)
    if any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
        return func(**kwargs)
    supported_kwargs = {
        key: value
        for key, value in kwargs.items()
        if key in signature.parameters
    }
    return func(**supported_kwargs)


def _checkpointed_hitl_enabled(payload: RuntimeAgentRunRequest) -> bool:
    controls = payload.controls
    return bool(
        controls is not None
        and controls.hitl is not None
        and (
            (
                controls.hitl.subquestions is not None
                and controls.hitl.subquestions.enabled
            )
            or (
                controls.hitl.query_expansion is not None
                and controls.hitl.query_expansion.enabled
            )
        )
    )


def _event_sequence(event_id: str | None) -> int:
    if event_id is None:
        return 0
    _, _, raw_sequence = event_id.rpartition(":")
    try:
        return int(raw_sequence)
    except ValueError:
        return 0


def append_agent_run_event(job_id: str, event: RuntimeLifecycleEvent) -> None:
    with _JOB_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        job.lifecycle_events.append(event.model_copy(deep=True))


def _build_job_lifecycle_event(
    job: AgentRunJobStatus,
    *,
    event_type: str,
    stage: str,
    status: str,
    error: str | None = None,
    decomposition_sub_questions: list[str] | None = None,
    sub_question_artifacts: list[SubQuestionArtifacts] | None = None,
    sub_items: list[tuple[str, str]] | None = None,
    output: str | None = None,
    result: RuntimeAgentRunResponse | None = None,
    interrupt_payload: Any | None = None,
    checkpoint_id: str | None = None,
    elapsed_ms: int | None = None,
) -> RuntimeLifecycleEvent:
    previous_event_id = job.lifecycle_events[-1].event_id if job.lifecycle_events else None
    next_sequence = _event_sequence(previous_event_id) + 1
    return RuntimeLifecycleEvent(
        event_type=event_type,
        event_id=f"{job.run_id}:{next_sequence:06d}",
        run_id=job.run_id,
        thread_id=job.thread_id,
        trace_id=job.trace_id,
        stage=stage,
        status=status,
        emitted_at=datetime.now(timezone.utc).isoformat(),
        error=error,
        decomposition_sub_questions=decomposition_sub_questions,
        sub_question_artifacts=sub_question_artifacts,
        sub_items=sub_items,
        output=output,
        result=result,
        interrupt_payload=interrupt_payload,
        checkpoint_id=checkpoint_id,
        elapsed_ms=elapsed_ms,
    )


def _elapsed_ms(job: AgentRunJobStatus) -> int:
    finished_at = job.finished_at if job.finished_at is not None else time.time()
    return max(0, int(round((finished_at - job.started_at) * 1000)))


def list_agent_run_events(job_id: str, *, after_event_id: str | None = None) -> list[RuntimeLifecycleEvent]:
    with _JOB_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            raise SDKConfigurationError("Job not found.")
        min_sequence = _event_sequence(after_event_id)
        return [event.model_copy(deep=True) for event in job.lifecycle_events if _event_sequence(event.event_id) > min_sequence]


def iter_agent_run_events(
    job_id: str,
    *,
    after_event_id: str | None = None,
    poll_interval: float = 0.05,
):
    last_event_id = after_event_id
    while True:
        events = list_agent_run_events(job_id, after_event_id=last_event_id)
        for event in events:
            last_event_id = event.event_id
            yield event
            if event.event_type in _TERMINAL_LIFECYCLE_EVENT_TYPES:
                return
        terminal_status_reached = False
        with _JOB_LOCK:
            job = _JOBS.get(job_id)
            if job is None:
                return
            terminal_status_reached = job.status in {"success", "error", "cancelled", "paused"}
        if terminal_status_reached:
            trailing_events = list_agent_run_events(job_id, after_event_id=last_event_id)
            for event in trailing_events:
                last_event_id = event.event_id
                yield event
                if event.event_type in _TERMINAL_LIFECYCLE_EVENT_TYPES:
                    return
            return
        time.sleep(poll_interval)


def _persist_job_status(job: AgentRunJobStatus) -> None:
    session = SessionLocal()
    try:
        run = resolve_thread_identity(
            session=session,
            run_id=job.run_id,
            thread_id=job.thread_id,
            status=job.status,
            metadata={"job_id": job.job_id, "stage": job.stage, "query": job.query},
        )
        run.status = job.status
        metadata = dict(run.metadata_json or {})
        metadata.update(
            {
                "job_id": job.job_id,
                "stage": job.stage,
                "message": job.message,
                "query": job.query,
                "request_payload": dict(job.request_payload),
            }
        )
        if job.interrupt_payload is not None:
            metadata["interrupt_payload"] = job.interrupt_payload
        if job.checkpoint_id is not None:
            metadata["checkpoint_id"] = job.checkpoint_id
        run.metadata_json = metadata
        run.error_message = job.error
        if job.status in {"success", "error", "cancelled"}:
            run.completed_at = datetime.now(timezone.utc)
        if job.checkpoint_id:
            checkpoint_link = (
                session.query(RuntimeCheckpointLink)
                .filter(RuntimeCheckpointLink.run_id == job.run_id)
                .one_or_none()
            )
            if checkpoint_link is None:
                checkpoint_link = RuntimeCheckpointLink(
                    run_id=job.run_id,
                    thread_id=job.thread_id,
                    checkpoint_id=job.checkpoint_id,
                    checkpoint_metadata={"job_id": job.job_id},
                    is_latest=True,
                )
                session.add(checkpoint_link)
            else:
                checkpoint_link.thread_id = job.thread_id
                checkpoint_link.checkpoint_id = job.checkpoint_id
                checkpoint_link.checkpoint_metadata = {"job_id": job.job_id}
                checkpoint_link.is_latest = True
        session.commit()
    finally:
        session.close()


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
    run_metadata = build_graph_run_metadata(run_id=job_id, thread_id=payload.thread_id)
    normalized_request_payload = payload.model_dump(mode="json", exclude_none=True)
    status = AgentRunJobStatus(
        job_id=job_id,
        run_id=run_metadata.run_id,
        thread_id=run_metadata.thread_id,
        status="running",
        trace_id=run_metadata.trace_id,
        query=payload.query,
        request_payload=normalized_request_payload,
        message="Run queued.",
        stage="queued",
        runtime_model=model,
        runtime_vector_store=vector_store,
    )
    with _JOB_LOCK:
        _JOBS[job_id] = status
    _persist_job_status(status)
    logger.info(
        "Runtime async job created job_id=%s run_id=%s has_model=%s has_vector_store=%s",
        job_id,
        run_metadata.run_id,
        model is not None,
        vector_store is not None,
    )
    _EXECUTOR.submit(_run_agent_job, job_id, payload, run_metadata.run_id, run_metadata.thread_id, model, vector_store)
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
        _persist_job_status(job)
        logger.info("Runtime async job cancel requested job_id=%s run_id=%s", job.job_id, job.run_id)
        return True


def resume_agent_run_job(job_id: str, *, resume: Any = True) -> AgentRunJobStatus:
    with _JOB_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            raise SDKConfigurationError("Job not found.")
        try:
            ensure_resume_allowed(job.status)
        except ResumeTransitionError as exc:
            raise SDKConfigurationError(str(exc)) from exc
        if job.runtime_model is None or job.runtime_vector_store is None:
            raise SDKConfigurationError("Job cannot be resumed because runtime dependencies are unavailable.")
        try:
            normalized_resume = normalize_resume_payload(resume, checkpoint_id=job.checkpoint_id)
        except ResumeTransitionError as exc:
            raise SDKConfigurationError(str(exc)) from exc
        job.status = "running"
        job.message = "Resuming from checkpoint."
        job.stage = "resuming"
        job.interrupt_payload = None
        job.finished_at = None
        request_payload = dict(job.request_payload)
        if not request_payload:
            request_payload = {"query": job.query}
        payload = RuntimeAgentRunRequest.model_validate(request_payload)
        model = job.runtime_model
        vector_store = job.runtime_vector_store
    _persist_job_status(job)
    _EXECUTOR.submit(_run_agent_job, job_id, payload, job.run_id, job.thread_id, model, vector_store, normalized_resume)
    return job


def _stage_from_snapshot(snapshot: GraphStageSnapshot) -> str:
    if snapshot.stage == "decompose":
        return "subquestions_ready"
    return snapshot.stage


def _run_agent_job(
    job_id: str,
    payload: RuntimeAgentRunRequest,
    run_id: str,
    thread_id: str,
    model: Any | None,
    vector_store: Any | None,
    resume: Any | None = None,
) -> None:
    job = get_agent_run_job(job_id)
    if job is None:
        return
    if job.cancel_requested:
        with _JOB_LOCK:
            job.status = "cancelled"
            job.message = "Cancelled before run started."
            job.finished_at = time.time()
        _persist_job_status(job)
        logger.info("Runtime async job cancelled before start job_id=%s run_id=%s", job_id, run_id)
        return

    logger.info("Runtime async job started job_id=%s run_id=%s query_len=%s", job_id, run_id, len(payload.query))
    with _JOB_LOCK:
        job.stage = "initializing"
        job.message = "Initializing vector store."
        if not job.request_payload:
            job.request_payload = payload.model_dump(mode="json", exclude_none=True)
    _persist_job_status(job)

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
            snapshot_event: RuntimeLifecycleEvent | None = None
            with _JOB_LOCK:
                current_job = _JOBS.get(job_id)
                if current_job is None:
                    return
                stage_metadata = AgentRunStageMetadata(
                    stage=mapped_stage,
                    status=snapshot.status,
                    sub_question=snapshot.sub_question,
                    lane_index=snapshot.lane_index,
                    lane_total=snapshot.lane_total,
                    emitted_at=time.time(),
                )
                current_job.stage = mapped_stage
                current_job.message = f"Stage completed: {mapped_stage}"
                current_job.stages.append(stage_metadata)
                current_job.decomposition_sub_questions = list(snapshot.decomposition_sub_questions)
                current_job.sub_question_artifacts = [item.model_copy(deep=True) for item in snapshot.sub_question_artifacts]
                current_job.sub_qa = [item.model_copy(deep=True) for item in snapshot.sub_qa]
                current_job.output = snapshot.output
                snapshot_event = _build_job_lifecycle_event(
                    current_job,
                    event_type="stage.snapshot",
                    stage=mapped_stage,
                    status=snapshot.status,
                    decomposition_sub_questions=list(snapshot.decomposition_sub_questions),
                    sub_question_artifacts=[item.model_copy(deep=True) for item in snapshot.sub_question_artifacts],
                    sub_items=[(item.sub_question, item.sub_answer) for item in snapshot.sub_qa],
                    output=snapshot.output,
                    elapsed_ms=_elapsed_ms(current_job),
                )
                current_job.lifecycle_events.append(snapshot_event)
            logger.info(
                "Runtime async job snapshot job_id=%s run_id=%s stage=%s lane_index=%s lane_total=%s subquestions=%s",
                job_id,
                run_id,
                mapped_stage,
                snapshot.lane_index,
                snapshot.lane_total,
                len(snapshot.decomposition_sub_questions),
            )

        run_metadata = build_graph_run_metadata(run_id=run_id, thread_id=thread_id)
        if resume is None and not _checkpointed_hitl_enabled(payload):
            state = _call_with_supported_kwargs(
                execute_runtime_graph,
                context=RuntimeGraphContext(
                    payload=payload,
                    model=model,
                    vector_store=resolved_vector_store,
                    initial_search_context=initial_search_context,
                ),
                run_metadata=run_metadata,
                lifecycle_callback=lambda event: append_agent_run_event(job_id, event),
                snapshot_callback=on_snapshot,
                emit_success_terminal_event=False,
            )
            outcome = type(
                "GraphExecutionOutcome",
                (),
                {
                    "status": "completed",
                    "state": state,
                    "response": map_graph_state_to_runtime_response(state),
                    "interrupt_payload": None,
                    "checkpoint_id": None,
                },
            )()
        else:
            outcome = _call_with_supported_kwargs(
                run_checkpointed_agent,
                payload=payload,
                vector_store=resolved_vector_store,
                model=model,
                run_metadata=run_metadata,
                initial_search_context=initial_search_context,
                lifecycle_callback=lambda event: append_agent_run_event(job_id, event),
                snapshot_callback=on_snapshot,
                resume=resume,
                emit_success_terminal_event=False,
                emit_paused_terminal_event=False,
            )
        if outcome.status == "paused":
            with _JOB_LOCK:
                current_job = _JOBS.get(job_id)
                if current_job is None:
                    return
                resolved_interrupt_payload = attach_checkpoint_metadata(
                    outcome.interrupt_payload,
                    checkpoint_id=outcome.checkpoint_id,
                    thread_id=current_job.thread_id,
                )
                pause_stage = (
                    str(current_job.interrupt_payload.get("stage", "")).strip()
                    if isinstance(current_job.interrupt_payload, dict)
                    else ""
                )
                if not pause_stage and isinstance(resolved_interrupt_payload, dict):
                    pause_stage = str(resolved_interrupt_payload.get("stage", "")).strip()
                if not pause_stage:
                    pause_stage = current_job.stage or "paused"
                current_job.status = "paused"
                current_job.message = "Paused and awaiting resume input."
                current_job.stage = pause_stage
                current_job.interrupt_payload = resolved_interrupt_payload
                current_job.checkpoint_id = outcome.checkpoint_id
                current_job.lifecycle_events.append(
                    _build_job_lifecycle_event(
                        current_job,
                        event_type="run.paused",
                        stage=pause_stage,
                        status="paused",
                        decomposition_sub_questions=list(current_job.decomposition_sub_questions),
                        sub_question_artifacts=[item.model_copy(deep=True) for item in current_job.sub_question_artifacts],
                        sub_items=[(item.sub_question, item.sub_answer) for item in current_job.sub_qa],
                        output=current_job.output,
                        interrupt_payload=resolved_interrupt_payload,
                        checkpoint_id=outcome.checkpoint_id,
                        elapsed_ms=_elapsed_ms(current_job),
                    )
                )
            _persist_job_status(current_job)
            logger.info(
                "Runtime async job paused job_id=%s run_id=%s checkpoint_id=%s",
                job_id,
                run_id,
                outcome.checkpoint_id,
            )
            return
        state = outcome.state
        response = outcome.response
        if state is None or response is None:
            raise SDKConfigurationError("Runtime execution completed without a durable result payload.")
        rag_state = to_rag_state(state)
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
            current_job.interrupt_payload = None
            current_job.checkpoint_id = outcome.checkpoint_id
            current_job.sub_qa = [item.model_copy(deep=True) for item in rag_state["sub_qa"]]
            current_job.decomposition_sub_questions = list(rag_state["decomposition_sub_questions"])
            current_job.sub_question_artifacts = [item.model_copy(deep=True) for item in rag_state["sub_question_artifacts"]]
            current_job.output = response.output
            current_job.finished_at = time.time()
            current_job.lifecycle_events.append(
                _build_job_lifecycle_event(
                    current_job,
                    event_type="run.completed",
                    stage=current_job.stage,
                    status=current_job.status,
                    decomposition_sub_questions=list(current_job.decomposition_sub_questions),
                    sub_question_artifacts=[item.model_copy(deep=True) for item in current_job.sub_question_artifacts],
                    sub_items=[(item.sub_question, item.sub_answer) for item in current_job.sub_qa],
                    output=current_job.output,
                    result=current_job.result.model_copy(deep=True) if current_job.result is not None else None,
                    elapsed_ms=_elapsed_ms(current_job),
                )
            )
        _persist_job_status(current_job)
        logger.info(
            "Runtime async job finished job_id=%s run_id=%s status=%s sub_qa_count=%s output_len=%s",
            job_id,
            run_id,
            current_job.status,
            len(response.sub_items),
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
        _persist_job_status(current_job)
