from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from benchmarks.datasets import BenchmarkQuestion, load_benchmark_questions
from config import BenchmarkRuntimeSettings, get_benchmark_context_fingerprint
from db import SessionLocal
from models import BenchmarkResult, BenchmarkRun, BenchmarkRunMode
from schemas import BenchmarkMode, BenchmarkTargets
from services.benchmark_artifact_registry import BenchmarkArtifactRegistry
from services.benchmark_execution_adapter import BenchmarkExecutionAdapter
from services.benchmark_modes import get_mode_runtime_overrides
from services.benchmark_quality_service import BenchmarkQualityService
from services.benchmark_retrieval_metrics_service import BenchmarkRetrievalMetricsService

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_ROOT = BACKEND_ROOT / "benchmarks" / "datasets"


@dataclass(frozen=True)
class BenchmarkRunSummary:
    run_id: str
    dataset_id: str
    mode_count: int
    question_count: int
    completed_results: int


class BenchmarkRunner:
    """Synchronous benchmark runner for mode x question execution."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] = SessionLocal,
        execution_adapter: BenchmarkExecutionAdapter | None = None,
        quality_service: BenchmarkQualityService | None = None,
        retrieval_metrics_service: BenchmarkRetrievalMetricsService | None = None,
        dataset_root: Path = DEFAULT_DATASET_ROOT,
        runtime_settings: BenchmarkRuntimeSettings | None = None,
        artifact_registry: BenchmarkArtifactRegistry | None = None,
        progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._execution_adapter = execution_adapter or BenchmarkExecutionAdapter()
        self._quality_service = quality_service or BenchmarkQualityService(session_factory=session_factory)
        self._retrieval_metrics_service = retrieval_metrics_service or BenchmarkRetrievalMetricsService(
            session_factory=session_factory
        )
        self._dataset_root = dataset_root
        self._runtime_settings = runtime_settings or BenchmarkRuntimeSettings.from_env()
        self._artifact_registry = artifact_registry or BenchmarkArtifactRegistry()
        self._progress_callback = progress_callback

    def run(
        self,
        *,
        dataset_id: str,
        modes: list[BenchmarkMode | str],
        vector_store: Any,
        model: Any,
        run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        targets: BenchmarkTargets | None = None,
        progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> BenchmarkRunSummary:
        resolved_modes = [mode if isinstance(mode, BenchmarkMode) else BenchmarkMode(mode) for mode in modes]
        if not resolved_modes:
            raise ValueError("At least one benchmark mode is required")

        resolved_run_id = run_id or f"benchmark-run-{uuid.uuid4()}"
        dataset_path = self._dataset_path(dataset_id)
        questions = load_benchmark_questions(dataset_path)
        corpus_hash = self._compute_dataset_hash(dataset_path)

        logger.info(
            "Benchmark runner start run_id=%s dataset_id=%s mode_count=%s question_count=%s",
            resolved_run_id,
            dataset_id,
            len(resolved_modes),
            len(questions),
        )

        with self._session_factory() as session:
            run = self._initialize_run(
                session=session,
                run_id=resolved_run_id,
                dataset_id=dataset_id,
                modes=resolved_modes,
                corpus_hash=corpus_hash,
                metadata=metadata or {},
                targets=targets,
                runtime_model=str(model),
            )
            run.status = "running"
            run.error = None
            run.started_at = run.started_at or datetime.now(timezone.utc)
            run.finished_at = None
            session.commit()

            completed_results = 0
            try:
                for mode in resolved_modes:
                    completed_results += self._run_mode(
                        session=session,
                        run_id=resolved_run_id,
                        mode=mode,
                        questions=questions,
                        vector_store=vector_store,
                        model=model,
                        progress_callback=progress_callback,
                    )
                run.status = "completed"
                run.error = None
                run.finished_at = datetime.now(timezone.utc)
                session.commit()
            except Exception as exc:  # noqa: BLE001
                run.status = "failed"
                run.error = str(exc)
                run.finished_at = datetime.now(timezone.utc)
                session.commit()
                logger.exception("Benchmark runner failed run_id=%s error=%s", resolved_run_id, exc)
                raise

        logger.info(
            "Benchmark runner complete run_id=%s dataset_id=%s completed_results=%s",
            resolved_run_id,
            dataset_id,
            completed_results,
        )
        return BenchmarkRunSummary(
            run_id=resolved_run_id,
            dataset_id=dataset_id,
            mode_count=len(resolved_modes),
            question_count=len(questions),
            completed_results=completed_results,
        )

    def _run_mode(
        self,
        *,
        session: Session,
        run_id: str,
        mode: BenchmarkMode,
        questions: list[BenchmarkQuestion],
        vector_store: Any,
        model: Any,
        progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> int:
        successful_ids = self._get_successful_question_ids(session=session, run_id=run_id, mode=mode.value)
        mode_overrides = get_mode_runtime_overrides(mode)
        run = session.get(BenchmarkRun, run_id)
        run_metadata = run.run_metadata if run is not None else None
        completed = 0
        logger.info(
            "Benchmark runner mode start run_id=%s mode=%s question_count=%s successful_cached=%s",
            run_id,
            mode.value,
            len(questions),
            len(successful_ids),
        )
        self._emit_progress(
            "mode_started",
            {
                "run_id": run_id,
                "mode": mode.value,
                "question_count": len(questions),
            },
            progress_callback=progress_callback,
        )
        for index, question in enumerate(questions, start=1):
            if question.question_id in successful_ids:
                logger.info(
                    "Benchmark runner skip cached result run_id=%s mode=%s question_id=%s",
                    run_id,
                    mode.value,
                    question.question_id,
                )
                continue

            question_started = time.perf_counter()
            response = None
            execution_error = None
            result_row: BenchmarkResult | None = None
            stage_timings: dict[str, int] = {}
            try:
                response = self._execution_adapter.run_sync(
                    question.question,
                    vector_store=vector_store,
                    model=model,
                    config=mode_overrides,
                )
            except Exception as exc:  # noqa: BLE001
                execution_error = str(exc)
                logger.exception(
                    "Benchmark runner question failed run_id=%s mode=%s question_id=%s index=%s/%s error=%s",
                    run_id,
                    mode.value,
                    question.question_id,
                    index,
                    len(questions),
                    exc,
                )
            stage_timings["runtime_execution_ms"] = int((time.perf_counter() - question_started) * 1000)

            persist_started = time.perf_counter()
            result_row = self._upsert_result(
                session=session,
                run_id=run_id,
                mode=mode.value,
                question_id=question.question_id,
                answer_payload=response.model_dump(mode="json") if response is not None else None,
                citations=[row.model_dump(mode="json") for row in (response.final_citations if response else [])],
                e2e_latency_ms=stage_timings["runtime_execution_ms"],
                stage_timings=stage_timings,
                timing_outcome=self._classify_timing_outcome(execution_error),
                latency_ms=stage_timings["runtime_execution_ms"],
                token_usage=None,
                execution_error=execution_error,
            )
            session.commit()
            stage_timings["persist_result_ms"] = int((time.perf_counter() - persist_started) * 1000)
            completed += 1
            logger.info(
                "Benchmark runner persisted result run_id=%s mode=%s question_id=%s e2e_latency_ms=%s timing_outcome=%s stage_timings=%s has_error=%s",
                run_id,
                mode.value,
                question.question_id,
                result_row.e2e_latency_ms if result_row is not None else None,
                result_row.timing_outcome if result_row is not None else None,
                stage_timings,
                execution_error is not None,
            )
            if result_row is not None:
                retrieval_k = self._resolve_retrieval_k(run_metadata=run_metadata)
                try:
                    retrieval_row = self._retrieval_metrics_service.evaluate_and_persist(
                        result_id=result_row.id,
                        k=retrieval_k,
                    )
                    logger.info(
                        "Benchmark runner retrieval diagnostics complete run_id=%s mode=%s question_id=%s recall_at_k=%s mrr=%s ndcg=%s",
                        run_id,
                        mode.value,
                        question.question_id,
                        retrieval_row.recall_at_k,
                        retrieval_row.mrr,
                        retrieval_row.ndcg,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "Benchmark runner retrieval diagnostics failed run_id=%s mode=%s question_id=%s error=%s",
                        run_id,
                        mode.value,
                        question.question_id,
                        exc,
                    )

            if execution_error is None and result_row is not None:
                quality_started = time.perf_counter()
                self._emit_progress(
                    "quality_evaluation_started",
                    {
                        "run_id": run_id,
                        "mode": mode.value,
                        "question_id": question.question_id,
                    },
                    progress_callback=progress_callback,
                )
                try:
                    quality_row = self._quality_service.evaluate_and_persist(
                        result_id=result_row.id,
                        question_text=question.question,
                        expected_answer_points=question.expected_answer_points,
                        required_sources=question.required_sources,
                        run_metadata=run_metadata,
                    )
                    logger.info(
                        "Benchmark runner quality scoring complete run_id=%s mode=%s question_id=%s score=%.4f passed=%s",
                        run_id,
                        mode.value,
                        question.question_id,
                        quality_row.score,
                        quality_row.passed,
                    )
                    self._emit_progress(
                        "quality_evaluation_completed",
                        {
                            "run_id": run_id,
                            "mode": mode.value,
                            "question_id": question.question_id,
                            "score": quality_row.score,
                            "passed": quality_row.passed,
                        },
                        progress_callback=progress_callback,
                    )
                except Exception as exc:  # noqa: BLE001
                    error_message = str(exc)
                    logger.exception(
                        "Benchmark runner quality scoring failed run_id=%s mode=%s question_id=%s error=%s",
                        run_id,
                        mode.value,
                        question.question_id,
                        error_message,
                    )
                    self._append_quality_evaluation_error(
                        session=session,
                        run_id=run_id,
                        mode=mode.value,
                        question_id=question.question_id,
                        error=error_message,
                    )
                    session.commit()
                    self._emit_progress(
                        "quality_evaluation_failed",
                        {
                            "run_id": run_id,
                            "mode": mode.value,
                            "question_id": question.question_id,
                            "error": error_message,
                        },
                        progress_callback=progress_callback,
                    )
                finally:
                    stage_timings["quality_evaluation_ms"] = int((time.perf_counter() - quality_started) * 1000)
                    e2e_latency_ms = int((time.perf_counter() - question_started) * 1000)
                    result_row = self._upsert_result(
                        session=session,
                        run_id=run_id,
                        mode=mode.value,
                        question_id=question.question_id,
                        answer_payload=response.model_dump(mode="json") if response is not None else None,
                        citations=[row.model_dump(mode="json") for row in (response.final_citations if response else [])],
                        e2e_latency_ms=e2e_latency_ms,
                        stage_timings=stage_timings,
                        timing_outcome=self._classify_timing_outcome(execution_error),
                        latency_ms=e2e_latency_ms,
                        token_usage=None,
                        execution_error=execution_error,
                    )
                    session.commit()
                    logger.info(
                        "Benchmark runner updated timings after quality evaluation run_id=%s mode=%s question_id=%s stage_timings=%s",
                        run_id,
                        mode.value,
                        question.question_id,
                        stage_timings,
                    )

            if execution_error is not None:
                e2e_latency_ms = int((time.perf_counter() - question_started) * 1000)
                result_row = self._upsert_result(
                    session=session,
                    run_id=run_id,
                    mode=mode.value,
                    question_id=question.question_id,
                    answer_payload=response.model_dump(mode="json") if response is not None else None,
                    citations=[row.model_dump(mode="json") for row in (response.final_citations if response else [])],
                    e2e_latency_ms=e2e_latency_ms,
                    stage_timings=stage_timings,
                    timing_outcome=self._classify_timing_outcome(execution_error),
                    latency_ms=e2e_latency_ms,
                    token_usage=None,
                    execution_error=execution_error,
                )
                session.commit()
                logger.info(
                    "Benchmark runner finalized error timing run_id=%s mode=%s question_id=%s e2e_latency_ms=%s timing_outcome=%s stage_timings=%s",
                    run_id,
                    mode.value,
                    question.question_id,
                    result_row.e2e_latency_ms if result_row is not None else None,
                    result_row.timing_outcome if result_row is not None else None,
                    stage_timings,
                )
                raise RuntimeError(execution_error)
        return completed

    def _initialize_run(
        self,
        *,
        session: Session,
        run_id: str,
        dataset_id: str,
        modes: list[BenchmarkMode],
        corpus_hash: str,
        metadata: dict[str, Any],
        targets: BenchmarkTargets | None,
        runtime_model: str,
    ) -> BenchmarkRun:
        run = session.get(BenchmarkRun, run_id)
        mode_values = [mode.value for mode in modes]
        resolved_run_metadata = self._build_run_metadata_with_artifacts(
            dataset_id=dataset_id,
            run_id=run_id,
            metadata=metadata,
        )

        if run is None:
            run = BenchmarkRun(
                run_id=run_id,
                status="queued",
                dataset_id=dataset_id,
                slo_snapshot=self._build_slo_snapshot(targets),
                context_fingerprint=get_benchmark_context_fingerprint(
                    self._runtime_settings,
                    runtime_model=runtime_model,
                    extra={"dataset_id": dataset_id, "modes": mode_values},
                ),
                corpus_hash=corpus_hash,
                objective_snapshot={"primary_kpi": "correctness", "secondary_kpi": "latency"},
                run_metadata=resolved_run_metadata,
            )
            session.add(run)
            session.flush()
            logger.info("Benchmark runner created run metadata run_id=%s", run_id)
        else:
            if run.dataset_id != dataset_id:
                raise ValueError(f"Existing run dataset mismatch: {run.dataset_id} != {dataset_id}")
            run.corpus_hash = corpus_hash
            if metadata:
                run.run_metadata = resolved_run_metadata
            logger.info("Benchmark runner reusing run metadata run_id=%s status=%s", run_id, run.status)

        existing_mode_rows = session.scalars(select(BenchmarkRunMode).where(BenchmarkRunMode.run_id == run_id)).all()
        existing_modes = {row.mode for row in existing_mode_rows}
        for mode in modes:
            if mode.value in existing_modes:
                continue
            session.add(
                BenchmarkRunMode(
                    run_id=run_id,
                    mode=mode.value,
                    mode_metadata={"runtime_config_overrides": get_mode_runtime_overrides(mode)},
                )
            )
        session.flush()
        return run

    def _build_run_metadata_with_artifacts(
        self,
        *,
        dataset_id: str,
        run_id: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        run_metadata = dict(metadata)
        run_metadata["artifact_versions"] = self._artifact_registry.resolve_for_run(
            dataset_id=dataset_id,
            run_id=run_id,
            run_metadata=run_metadata,
        )
        logger.info(
            "Benchmark runner resolved artifact versions run_id=%s dataset_id=%s prompt_version=%s reference_version=%s",
            run_id,
            dataset_id,
            run_metadata["artifact_versions"]["prompt"]["version"],
            run_metadata["artifact_versions"]["reference_report"]["version"],
        )
        return run_metadata

    def _upsert_result(
        self,
        *,
        session: Session,
        run_id: str,
        mode: str,
        question_id: str,
        answer_payload: dict[str, Any] | None,
        citations: list[dict[str, Any]],
        e2e_latency_ms: int,
        stage_timings: dict[str, int],
        timing_outcome: str,
        latency_ms: int,
        token_usage: dict[str, Any] | None,
        execution_error: str | None,
    ) -> BenchmarkResult:
        row = session.scalar(
            select(BenchmarkResult).where(
                BenchmarkResult.run_id == run_id,
                BenchmarkResult.mode == mode,
                BenchmarkResult.question_id == question_id,
            )
        )
        if row is None:
            row = BenchmarkResult(run_id=run_id, mode=mode, question_id=question_id)
            session.add(row)
        row.answer_payload = answer_payload
        row.citations = citations
        row.e2e_latency_ms = e2e_latency_ms
        row.stage_timings = dict(stage_timings)
        row.timing_outcome = timing_outcome
        row.latency_ms = latency_ms
        row.token_usage = token_usage
        row.execution_error = execution_error
        session.flush()
        return row

    def _classify_timing_outcome(self, execution_error: str | None) -> str:
        if execution_error is None:
            return "completed"
        lowered = execution_error.lower()
        if "cancel" in lowered:
            return "cancelled"
        if "timeout" in lowered or "timed out" in lowered:
            return "timeout"
        return "error"

    def _append_quality_evaluation_error(
        self,
        *,
        session: Session,
        run_id: str,
        mode: str,
        question_id: str,
        error: str,
    ) -> None:
        run = session.get(BenchmarkRun, run_id)
        if run is None:
            return
        metadata = dict(run.run_metadata or {})
        evaluation_errors = metadata.get("evaluation_errors")
        if not isinstance(evaluation_errors, list):
            evaluation_errors = []
        evaluation_errors.append(
            {
                "stage": "quality",
                "mode": mode,
                "question_id": question_id,
                "error": error,
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        metadata["evaluation_errors"] = evaluation_errors
        run.run_metadata = metadata
        logger.warning(
            "Benchmark runner captured non-fatal evaluation error run_id=%s mode=%s question_id=%s",
            run_id,
            mode,
            question_id,
        )

    def _emit_progress(
        self,
        event: str,
        payload: dict[str, Any],
        *,
        progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        callback = progress_callback or self._progress_callback
        if callback is None:
            return
        try:
            callback(event, payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Benchmark runner progress callback failed event=%s error=%s", event, exc)

    def _get_successful_question_ids(self, *, session: Session, run_id: str, mode: str) -> set[str]:
        rows = session.scalars(
            select(BenchmarkResult).where(
                BenchmarkResult.run_id == run_id,
                BenchmarkResult.mode == mode,
                BenchmarkResult.execution_error.is_(None),
            )
        ).all()
        return {row.question_id for row in rows}

    def _dataset_path(self, dataset_id: str) -> Path:
        path = self._dataset_root / dataset_id / "questions.jsonl"
        if not path.exists():
            raise ValueError(f"Benchmark dataset not found: {dataset_id}")
        return path

    def _compute_dataset_hash(self, dataset_path: Path) -> str:
        payload = dataset_path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        logger.info("Benchmark runner dataset hash computed path=%s hash=%s", dataset_path, digest)
        return digest

    def _build_slo_snapshot(self, targets: BenchmarkTargets | None) -> dict[str, Any]:
        target_values = targets or BenchmarkTargets(
            min_correctness=self._runtime_settings.target_min_correctness,
            max_latency_ms_p95=self._runtime_settings.target_p95_latency_ms,
            max_cost_usd=self._runtime_settings.target_max_cost_usd,
        )
        return json.loads(target_values.model_dump_json())

    @staticmethod
    def _resolve_retrieval_k(*, run_metadata: dict[str, Any] | None) -> int | None:
        if not isinstance(run_metadata, dict):
            return None
        raw = run_metadata.get("retrieval_metrics_k")
        if isinstance(raw, int) and raw > 0:
            return raw
        return None
