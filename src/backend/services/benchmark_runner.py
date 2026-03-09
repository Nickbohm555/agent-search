from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from benchmarks.datasets import BenchmarkQuestion, load_benchmark_questions
from config import BenchmarkRuntimeSettings, get_benchmark_context_fingerprint
from db import SessionLocal
from models import BenchmarkResult, BenchmarkRun, BenchmarkRunMode
from schemas import BenchmarkMode, BenchmarkTargets
from services.benchmark_execution_adapter import BenchmarkExecutionAdapter
from services.benchmark_modes import get_mode_runtime_overrides

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
        dataset_root: Path = DEFAULT_DATASET_ROOT,
        runtime_settings: BenchmarkRuntimeSettings | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._execution_adapter = execution_adapter or BenchmarkExecutionAdapter()
        self._dataset_root = dataset_root
        self._runtime_settings = runtime_settings or BenchmarkRuntimeSettings.from_env()

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
    ) -> int:
        successful_ids = self._get_successful_question_ids(session=session, run_id=run_id, mode=mode.value)
        mode_overrides = get_mode_runtime_overrides(mode)
        completed = 0
        logger.info(
            "Benchmark runner mode start run_id=%s mode=%s question_count=%s successful_cached=%s",
            run_id,
            mode.value,
            len(questions),
            len(successful_ids),
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

            started = time.perf_counter()
            response = None
            execution_error = None
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

            latency_ms = int((time.perf_counter() - started) * 1000)
            self._upsert_result(
                session=session,
                run_id=run_id,
                mode=mode.value,
                question_id=question.question_id,
                answer_payload=response.model_dump(mode="json") if response is not None else None,
                citations=[row.model_dump(mode="json") for row in (response.final_citations if response else [])],
                latency_ms=latency_ms,
                token_usage=None,
                execution_error=execution_error,
            )
            session.commit()
            completed += 1
            logger.info(
                "Benchmark runner persisted result run_id=%s mode=%s question_id=%s latency_ms=%s has_error=%s",
                run_id,
                mode.value,
                question.question_id,
                latency_ms,
                execution_error is not None,
            )

            if execution_error is not None:
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
                run_metadata=metadata,
            )
            session.add(run)
            session.flush()
            logger.info("Benchmark runner created run metadata run_id=%s", run_id)
        else:
            if run.dataset_id != dataset_id:
                raise ValueError(f"Existing run dataset mismatch: {run.dataset_id} != {dataset_id}")
            run.corpus_hash = corpus_hash
            run.run_metadata = metadata or run.run_metadata
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

    def _upsert_result(
        self,
        *,
        session: Session,
        run_id: str,
        mode: str,
        question_id: str,
        answer_payload: dict[str, Any] | None,
        citations: list[dict[str, Any]],
        latency_ms: int,
        token_usage: dict[str, Any] | None,
        execution_error: str | None,
    ) -> None:
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
        row.latency_ms = latency_ms
        row.token_usage = token_usage
        row.execution_error = execution_error

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
