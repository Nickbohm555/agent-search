from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models import BenchmarkResult
from schemas import BenchmarkMode, RuntimeAgentRunResponse
from services.benchmark_runner import BenchmarkRunner

DATABASE_URL = "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search"


def _write_dataset(tmp_path: Path, dataset_id: str) -> Path:
    dataset_dir = tmp_path / "benchmarks" / "datasets" / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = dataset_dir / "questions.jsonl"
    rows = [
        {
            "question_id": "DRB-LAT-001",
            "question": "How fast is this benchmark question?",
            "domain": "policy",
            "difficulty": "easy",
            "expected_answer_points": ["point-a"],
            "required_sources": ["source-a"],
            "disallowed_behaviors": ["hallucinate"],
        }
    ]
    with dataset_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    return tmp_path / "benchmarks" / "datasets"


class _NoOpQualityService:
    @dataclass
    class _QualityRow:
        score: float
        passed: bool

    def evaluate_and_persist(  # noqa: D401, PLR0913, ANN001
        self,
        *,
        result_id: int,
        question_text: str,
        expected_answer_points: list[str],
        required_sources: list[str],
        run_metadata=None,
        rubric_version: str = "v1",
        pass_threshold=None,
    ):
        del result_id, question_text, expected_answer_points, required_sources, run_metadata, rubric_version, pass_threshold
        return self._QualityRow(score=1.0, passed=True)


class _SuccessAdapter:
    def run_sync(self, query: str, *, vector_store, model, config=None):  # noqa: ANN001
        del vector_store, model, config
        return RuntimeAgentRunResponse(output=f"answer::{query}", final_citations=[])


class _ErrorAdapter:
    def __init__(self, message: str) -> None:
        self._message = message

    def run_sync(self, query: str, *, vector_store, model, config=None):  # noqa: ANN001
        del query, vector_store, model, config
        raise RuntimeError(self._message)


def test_benchmark_runner_persists_e2e_and_stage_timings(tmp_path: Path) -> None:
    dataset_root = _write_dataset(tmp_path, "tiny_latency_v1")
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    runner = BenchmarkRunner(
        session_factory=session_factory,
        execution_adapter=_SuccessAdapter(),
        quality_service=_NoOpQualityService(),
        dataset_root=dataset_root,
    )
    run_id = f"run-benchmark-latency-{uuid.uuid4()}"

    summary = runner.run(
        run_id=run_id,
        dataset_id="tiny_latency_v1",
        modes=[BenchmarkMode.agentic_default],
        vector_store=object(),
        model="model-test",
    )

    assert summary.completed_results == 1

    with Session(engine) as session:
        result = session.scalar(select(BenchmarkResult).where(BenchmarkResult.run_id == run_id))
        assert result is not None
        assert result.e2e_latency_ms is not None
        assert result.e2e_latency_ms >= 0
        assert result.stage_timings is not None
        assert result.stage_timings["runtime_execution_ms"] >= 0
        assert result.stage_timings["quality_evaluation_ms"] >= 0
        assert result.timing_outcome == "completed"


def test_benchmark_runner_classifies_timeout_and_cancel_timing_outcomes(tmp_path: Path) -> None:
    dataset_root = _write_dataset(tmp_path, "tiny_latency_v2")
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    timeout_runner = BenchmarkRunner(
        session_factory=session_factory,
        execution_adapter=_ErrorAdapter("runtime timeout while executing"),
        quality_service=_NoOpQualityService(),
        dataset_root=dataset_root,
    )
    timeout_run_id = f"run-benchmark-timeout-{uuid.uuid4()}"
    try:
        timeout_runner.run(
            run_id=timeout_run_id,
            dataset_id="tiny_latency_v2",
            modes=[BenchmarkMode.agentic_default],
            vector_store=object(),
            model="model-test",
        )
        assert False, "Expected timeout benchmark run to raise"
    except RuntimeError as exc:
        assert "runtime timeout" in str(exc)

    cancel_runner = BenchmarkRunner(
        session_factory=session_factory,
        execution_adapter=_ErrorAdapter("request cancelled by operator"),
        quality_service=_NoOpQualityService(),
        dataset_root=dataset_root,
    )
    cancel_run_id = f"run-benchmark-cancel-{uuid.uuid4()}"
    try:
        cancel_runner.run(
            run_id=cancel_run_id,
            dataset_id="tiny_latency_v2",
            modes=[BenchmarkMode.agentic_default],
            vector_store=object(),
            model="model-test",
        )
        assert False, "Expected cancelled benchmark run to raise"
    except RuntimeError as exc:
        assert "cancelled" in str(exc)

    with Session(engine) as session:
        timeout_result = session.scalar(select(BenchmarkResult).where(BenchmarkResult.run_id == timeout_run_id))
        assert timeout_result is not None
        assert timeout_result.timing_outcome == "timeout"
        assert timeout_result.stage_timings is not None
        assert timeout_result.stage_timings["runtime_execution_ms"] >= 0

        cancel_result = session.scalar(select(BenchmarkResult).where(BenchmarkResult.run_id == cancel_run_id))
        assert cancel_result is not None
        assert cancel_result.timing_outcome == "cancelled"
        assert cancel_result.stage_timings is not None
        assert cancel_result.stage_timings["runtime_execution_ms"] >= 0
