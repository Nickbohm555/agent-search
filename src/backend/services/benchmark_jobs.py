from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from langchain_openai import ChatOpenAI
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from db import DATABASE_URL, SessionLocal
from models import BenchmarkQualityScore, BenchmarkResult, BenchmarkRetrievalMetric, BenchmarkRun, BenchmarkRunMode
from schemas import (
    BenchmarkMode,
    BenchmarkModeSummary,
    BenchmarkObjective,
    BenchmarkResultQualityScore,
    BenchmarkResultRetrievalDiagnostics,
    BenchmarkResultStatusItem,
    BenchmarkRunCreateRequest,
    BenchmarkRunCreateResponse,
    BenchmarkRunListItem,
    BenchmarkRunListResponse,
    BenchmarkRunStatus,
    BenchmarkRunStatusResponse,
)
from services.benchmark_runner import BenchmarkRunner
from services.vector_store_service import get_vector_store
from utils.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=2)
_JOB_LOCK = threading.Lock()

_VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")
_BENCHMARK_MODEL_NAME = os.getenv("RUNTIME_AGENT_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
_BENCHMARK_MODEL_TEMPERATURE = float(os.getenv("DECOMPOSITION_ONLY_TEMPERATURE", "0"))


@dataclass
class BenchmarkRunJobStatus:
    job_id: str
    run_id: str
    status: str
    message: str = "Run queued."
    error: str | None = None
    cancel_requested: bool = False
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None


_JOBS: dict[str, BenchmarkRunJobStatus] = {}


def _to_benchmark_status(raw: str) -> BenchmarkRunStatus:
    try:
        return BenchmarkRunStatus(raw)
    except ValueError:
        logger.warning("Unknown benchmark run status mapped to failed status=%s", raw)
        return BenchmarkRunStatus.failed


def _epoch_or_none(timestamp: datetime | None) -> float | None:
    if timestamp is None:
        return None
    return timestamp.replace(tzinfo=timezone.utc).timestamp() if timestamp.tzinfo is None else timestamp.timestamp()


def _build_runtime_dependencies() -> tuple[object, object]:
    vector_store = get_vector_store(
        connection=DATABASE_URL,
        collection_name=_VECTOR_COLLECTION_NAME,
        embeddings=get_embedding_model(),
    )
    model = ChatOpenAI(
        model=_BENCHMARK_MODEL_NAME,
        temperature=_BENCHMARK_MODEL_TEMPERATURE,
    )
    logger.info(
        "Benchmark jobs dependencies resolved collection_name=%s model=%s",
        _VECTOR_COLLECTION_NAME,
        _BENCHMARK_MODEL_NAME,
    )
    return vector_store, model


def start_benchmark_run_job(
    payload: BenchmarkRunCreateRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
    runner: BenchmarkRunner | None = None,
) -> BenchmarkRunCreateResponse:
    job_id = str(uuid.uuid4())
    run_id = f"benchmark-run-{uuid.uuid4()}"
    status = BenchmarkRunJobStatus(
        job_id=job_id,
        run_id=run_id,
        status=BenchmarkRunStatus.queued.value,
        message="Run queued.",
    )
    with _JOB_LOCK:
        _JOBS[job_id] = status
    logger.info(
        "Benchmark run job created job_id=%s run_id=%s dataset_id=%s mode_count=%s",
        job_id,
        run_id,
        payload.dataset_id,
        len(payload.modes),
    )
    _EXECUTOR.submit(_run_benchmark_job, job_id, payload, session_factory, runner)
    return BenchmarkRunCreateResponse(run_id=run_id, status=BenchmarkRunStatus.queued)


def list_benchmark_runs(*, db: Session) -> BenchmarkRunListResponse:
    runs = db.scalars(select(BenchmarkRun).order_by(BenchmarkRun.created_at.desc())).all()
    items: list[BenchmarkRunListItem] = []
    for run in runs:
        mode_rows = db.scalars(select(BenchmarkRunMode).where(BenchmarkRunMode.run_id == run.run_id)).all()
        parsed_modes = [BenchmarkMode(row.mode) for row in mode_rows if row.mode in BenchmarkMode._value2member_map_]
        items.append(
            BenchmarkRunListItem(
                run_id=run.run_id,
                status=_to_benchmark_status(run.status),
                dataset_id=run.dataset_id,
                modes=parsed_modes,
                created_at=_epoch_or_none(run.created_at),
                started_at=_epoch_or_none(run.started_at),
                finished_at=_epoch_or_none(run.finished_at),
            )
        )
    logger.info("Benchmark runs listed count=%s", len(items))
    return BenchmarkRunListResponse(runs=items)


def get_benchmark_run_status(*, run_id: str, db: Session) -> BenchmarkRunStatusResponse | None:
    run = db.get(BenchmarkRun, run_id)
    if run is None:
        return None

    mode_rows = db.scalars(select(BenchmarkRunMode).where(BenchmarkRunMode.run_id == run_id)).all()
    mode_values = [row.mode for row in mode_rows]
    parsed_modes = [BenchmarkMode(mode) for mode in mode_values if mode in BenchmarkMode._value2member_map_]

    total_questions = (
        db.scalar(select(func.count()).select_from(BenchmarkResult).where(BenchmarkResult.run_id == run_id))
        or 0
    )
    completed_questions = (
        db.scalar(
            select(func.count()).select_from(BenchmarkResult).where(
                BenchmarkResult.run_id == run_id,
                BenchmarkResult.execution_error.is_(None),
            )
        )
        or 0
    )

    mode_summaries: list[BenchmarkModeSummary] = []
    for mode in parsed_modes:
        mode_total = (
            db.scalar(
                select(func.count()).select_from(BenchmarkResult).where(
                    BenchmarkResult.run_id == run_id,
                    BenchmarkResult.mode == mode.value,
                )
            )
            or 0
        )
        mode_completed = (
            db.scalar(
                select(func.count()).select_from(BenchmarkResult).where(
                    BenchmarkResult.run_id == run_id,
                    BenchmarkResult.mode == mode.value,
                    BenchmarkResult.execution_error.is_(None),
                )
            )
            or 0
        )
        correctness_rate = (mode_completed / mode_total) if mode_total > 0 else None
        mode_summaries.append(
            BenchmarkModeSummary(
                mode=mode,
                completed_questions=mode_completed,
                total_questions=mode_total,
                correctness_rate=correctness_rate,
                avg_latency_ms=None,
                p95_latency_ms=None,
            )
        )

    quality_rows = db.scalars(select(BenchmarkQualityScore).where(BenchmarkQualityScore.run_id == run_id)).all()
    quality_by_key = {(row.mode, row.question_id): row for row in quality_rows}
    retrieval_rows = db.scalars(select(BenchmarkRetrievalMetric).where(BenchmarkRetrievalMetric.run_id == run_id)).all()
    retrieval_by_key = {(row.mode, row.question_id): row for row in retrieval_rows}
    evaluation_error_by_key: dict[tuple[str, str], str] = {}
    if isinstance(run.run_metadata, dict):
        for item in run.run_metadata.get("evaluation_errors", []):
            if not isinstance(item, dict):
                continue
            if item.get("stage") != "quality":
                continue
            mode = item.get("mode")
            question_id = item.get("question_id")
            error = item.get("error")
            if isinstance(mode, str) and isinstance(question_id, str) and isinstance(error, str):
                evaluation_error_by_key[(mode, question_id)] = error

    result_rows = db.scalars(
        select(BenchmarkResult).where(BenchmarkResult.run_id == run_id).order_by(BenchmarkResult.mode, BenchmarkResult.question_id)
    ).all()
    results: list[BenchmarkResultStatusItem] = []
    for result in result_rows:
        key = (result.mode, result.question_id)
        quality_row = quality_by_key.get(key)
        retrieval_row = retrieval_by_key.get(key)
        quality_score = (
            BenchmarkResultQualityScore(
                score=quality_row.score,
                passed=quality_row.passed,
                rubric_version=quality_row.rubric_version,
                judge_model=quality_row.judge_model,
                subscores=quality_row.subscores_json if isinstance(quality_row.subscores_json, dict) else None,
                error=evaluation_error_by_key.get(key),
            )
            if quality_row is not None
            else (
                BenchmarkResultQualityScore(error=evaluation_error_by_key.get(key))
                if key in evaluation_error_by_key
                else None
            )
        )
        retrieval_diagnostics = (
            BenchmarkResultRetrievalDiagnostics(
                recall_at_k=retrieval_row.recall_at_k,
                mrr=retrieval_row.mrr,
                ndcg=retrieval_row.ndcg,
                k=retrieval_row.k,
                retrieved_document_ids=[
                    item for item in retrieval_row.retrieved_document_ids if isinstance(item, str)
                ]
                if isinstance(retrieval_row.retrieved_document_ids, list)
                else [],
                relevant_document_ids=[
                    item for item in retrieval_row.relevant_document_ids if isinstance(item, str)
                ]
                if isinstance(retrieval_row.relevant_document_ids, list)
                else [],
                label_source=retrieval_row.label_source,
            )
            if retrieval_row is not None
            else None
        )
        results.append(
            BenchmarkResultStatusItem(
                mode=result.mode,
                question_id=result.question_id,
                latency_ms=result.latency_ms,
                execution_error=result.execution_error,
                quality=quality_score,
                retrieval=retrieval_diagnostics,
            )
        )

    logger.info(
        "Benchmark run status resolved run_id=%s status=%s mode_count=%s completed=%s total=%s quality_scores=%s retrieval_metrics=%s",
        run_id,
        run.status,
        len(parsed_modes),
        completed_questions,
        total_questions,
        len(quality_rows),
        len(retrieval_rows),
    )
    return BenchmarkRunStatusResponse(
        run_id=run.run_id,
        status=_to_benchmark_status(run.status),
        dataset_id=run.dataset_id,
        modes=parsed_modes,
        objective=BenchmarkObjective(),
        targets=None,
        mode_summaries=mode_summaries,
        results=results,
        completed_questions=completed_questions,
        total_questions=total_questions,
        created_at=_epoch_or_none(run.created_at),
        started_at=_epoch_or_none(run.started_at),
        finished_at=_epoch_or_none(run.finished_at),
        error=run.error,
    )


def cancel_benchmark_run(*, run_id: str, db: Session) -> bool:
    run = db.get(BenchmarkRun, run_id)
    if run is None:
        return False
    if run.status in {BenchmarkRunStatus.completed.value, BenchmarkRunStatus.failed.value, BenchmarkRunStatus.cancelled.value}:
        return False

    run.status = BenchmarkRunStatus.cancelling.value
    db.commit()

    with _JOB_LOCK:
        for job in _JOBS.values():
            if job.run_id == run_id and job.status not in {"success", "error", "cancelled"}:
                job.cancel_requested = True
                job.status = BenchmarkRunStatus.cancelling.value
                job.message = "Cancellation requested."
                logger.info("Benchmark run cancel requested run_id=%s job_id=%s", run_id, job.job_id)
                return True

    logger.info("Benchmark run cancel requested for persisted-only run run_id=%s", run_id)
    return True


def _run_benchmark_job(
    job_id: str,
    payload: BenchmarkRunCreateRequest,
    session_factory: sessionmaker[Session],
    runner: BenchmarkRunner | None,
) -> None:
    with _JOB_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        run_id = job.run_id
        job.status = BenchmarkRunStatus.running.value
        job.message = "Run started."

    logger.info("Benchmark run job started job_id=%s run_id=%s", job_id, run_id)
    job_runner = runner or BenchmarkRunner(session_factory=session_factory)

    def _progress_callback(event: str, payload: dict[str, Any]) -> None:
        with _JOB_LOCK:
            current = _JOBS.get(job_id)
            if current is None:
                return
            if event == "quality_evaluation_started":
                current.message = "Running quality evaluation."
            elif event == "quality_evaluation_completed":
                current.message = "Quality evaluation completed."
            elif event == "quality_evaluation_failed":
                current.message = "Quality evaluation failed; continuing."
        logger.info(
            "Benchmark run job progress job_id=%s run_id=%s event=%s payload=%s",
            job_id,
            run_id,
            event,
            payload,
        )
    try:
        with _JOB_LOCK:
            current = _JOBS.get(job_id)
            if current is None:
                return
            if current.cancel_requested:
                with session_factory() as session:
                    run_row = session.get(BenchmarkRun, run_id)
                    if run_row is not None:
                        run_row.status = BenchmarkRunStatus.cancelled.value
                        run_row.finished_at = datetime.now(timezone.utc)
                        session.commit()
                current.status = BenchmarkRunStatus.cancelled.value
                current.message = "Cancelled."
                current.finished_at = time.time()
                logger.info("Benchmark run job cancelled before execution job_id=%s run_id=%s", job_id, run_id)
                return

        vector_store, model = _build_runtime_dependencies()
        job_runner.run(
            run_id=run_id,
            dataset_id=payload.dataset_id,
            modes=payload.modes,
            vector_store=vector_store,
            model=model,
            metadata=payload.metadata,
            targets=payload.targets,
            progress_callback=_progress_callback,
        )
        with _JOB_LOCK:
            current = _JOBS.get(job_id)
            if current is None:
                return
            if current.cancel_requested:
                current.status = BenchmarkRunStatus.cancelled.value
                current.message = "Cancelled."
            else:
                current.status = "success"
                current.message = "Completed."
            current.finished_at = time.time()
        logger.info("Benchmark run job finished job_id=%s run_id=%s", job_id, run_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Benchmark run job failed job_id=%s run_id=%s", job_id, run_id)
        with _JOB_LOCK:
            current = _JOBS.get(job_id)
            if current is None:
                return
            current.status = "error"
            current.message = "Failed."
            current.error = str(exc)
            current.finished_at = time.time()
