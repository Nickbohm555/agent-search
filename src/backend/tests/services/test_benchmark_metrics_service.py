from __future__ import annotations

import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models import BenchmarkQualityScore, BenchmarkResult, BenchmarkRun, BenchmarkRunMode
from schemas import BenchmarkMode
from services.benchmark_metrics_service import BenchmarkMetricsService
from services.benchmark_summary_service import BenchmarkSummaryService

DATABASE_URL = "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search"


def test_metrics_service_computes_percentiles_and_deterministic_pass_fail() -> None:
    service = BenchmarkMetricsService()
    thresholds = service.thresholds_from_snapshot({"min_correctness": 0.7, "max_latency_ms_p95": 300})
    result_rows = [
        BenchmarkResult(run_id="run-1", mode=BenchmarkMode.agentic_default.value, question_id="Q1", latency_ms=100),
        BenchmarkResult(run_id="run-1", mode=BenchmarkMode.agentic_default.value, question_id="Q2", latency_ms=220),
        BenchmarkResult(run_id="run-1", mode=BenchmarkMode.agentic_default.value, question_id="Q3", latency_ms=300),
        BenchmarkResult(run_id="run-1", mode=BenchmarkMode.agentic_default.value, question_id="Q4", latency_ms=150),
    ]
    quality_rows = [
        BenchmarkQualityScore(
            run_id="run-1",
            result_id=1,
            mode=BenchmarkMode.agentic_default.value,
            question_id="Q1",
            score=0.9,
            passed=True,
            rubric_version="v1",
            judge_model="judge",
        ),
        BenchmarkQualityScore(
            run_id="run-1",
            result_id=2,
            mode=BenchmarkMode.agentic_default.value,
            question_id="Q2",
            score=0.9,
            passed=True,
            rubric_version="v1",
            judge_model="judge",
        ),
        BenchmarkQualityScore(
            run_id="run-1",
            result_id=3,
            mode=BenchmarkMode.agentic_default.value,
            question_id="Q3",
            score=0.2,
            passed=False,
            rubric_version="v1",
            judge_model="judge",
        ),
    ]

    summary = service.aggregate(result_rows=result_rows, quality_rows=quality_rows, thresholds=thresholds)

    assert summary.total_questions == 4
    assert summary.completed_questions == 4
    assert summary.correctness_rate == 0.5
    assert summary.avg_latency_ms == 192.5
    assert summary.p95_latency_ms == 300.0
    assert summary.passed is False


def test_metrics_service_fails_when_required_signals_are_missing() -> None:
    service = BenchmarkMetricsService()
    thresholds = service.thresholds_from_snapshot({"min_correctness": 0.5, "max_latency_ms_p95": 1000})
    result_rows = [
        BenchmarkResult(
            run_id="run-2",
            mode=BenchmarkMode.agentic_default.value,
            question_id="Q1",
            latency_ms=None,
            execution_error="timeout",
        ),
    ]

    summary = service.aggregate(result_rows=result_rows, quality_rows=[], thresholds=thresholds)

    assert summary.total_questions == 1
    assert summary.completed_questions == 0
    assert summary.correctness_rate == 0.0
    assert summary.avg_latency_ms is None
    assert summary.p95_latency_ms is None
    assert summary.passed is False


def test_summary_service_aggregates_mode_and_run_metrics_from_db() -> None:
    engine = create_engine(DATABASE_URL, future=True)
    run_id = f"run-metrics-summary-{uuid.uuid4()}"

    with Session(engine) as session:
        run = BenchmarkRun(
            run_id=run_id,
            status="completed",
            dataset_id="internal_v1",
            slo_snapshot={"min_correctness": 0.6, "max_latency_ms_p95": 250},
            context_fingerprint=f"fingerprint-{run_id}",
            corpus_hash=f"corpus-{run_id}",
            objective_snapshot={"primary_kpi": "correctness"},
            run_metadata={"trigger": "metrics-summary-test"},
        )
        session.add(run)
        session.flush()

        session.add_all(
            [
                BenchmarkRunMode(run_id=run_id, mode=BenchmarkMode.agentic_default.value),
                BenchmarkRunMode(run_id=run_id, mode=BenchmarkMode.agentic_no_rerank.value),
            ]
        )
        r1 = BenchmarkResult(
            run_id=run_id,
            mode=BenchmarkMode.agentic_default.value,
            question_id="Q1",
            latency_ms=100,
            execution_error=None,
        )
        r2 = BenchmarkResult(
            run_id=run_id,
            mode=BenchmarkMode.agentic_default.value,
            question_id="Q2",
            latency_ms=180,
            execution_error=None,
        )
        r3 = BenchmarkResult(
            run_id=run_id,
            mode=BenchmarkMode.agentic_no_rerank.value,
            question_id="Q1",
            latency_ms=260,
            execution_error=None,
        )
        session.add_all([r1, r2, r3])
        session.flush()

        session.add_all(
            [
                BenchmarkQualityScore(
                    run_id=run_id,
                    result_id=r1.id,
                    mode=r1.mode,
                    question_id=r1.question_id,
                    score=0.9,
                    passed=True,
                    rubric_version="v1",
                    judge_model="judge",
                ),
                BenchmarkQualityScore(
                    run_id=run_id,
                    result_id=r2.id,
                    mode=r2.mode,
                    question_id=r2.question_id,
                    score=0.3,
                    passed=False,
                    rubric_version="v1",
                    judge_model="judge",
                ),
                BenchmarkQualityScore(
                    run_id=run_id,
                    result_id=r3.id,
                    mode=r3.mode,
                    question_id=r3.question_id,
                    score=0.8,
                    passed=True,
                    rubric_version="v1",
                    judge_model="judge",
                ),
            ]
        )
        session.commit()

    with Session(engine) as session:
        run = session.get(BenchmarkRun, run_id)
        assert run is not None
        summary = BenchmarkSummaryService().build_run_summary(
            db=session,
            run=run,
            parsed_modes=[BenchmarkMode.agentic_default, BenchmarkMode.agentic_no_rerank],
        )

    assert summary.total_questions == 3
    assert summary.completed_questions == 3
    assert round(summary.run_correctness_rate or 0.0, 4) == 0.6667
    assert summary.run_p95_latency_ms == 260.0
    assert summary.run_passed is False
    assert summary.mode_pass_fail == {
        BenchmarkMode.agentic_default.value: False,
        BenchmarkMode.agentic_no_rerank.value: False,
    }

    default_summary = next(item for item in summary.mode_summaries if item.mode == BenchmarkMode.agentic_default)
    assert default_summary.correctness_rate == 0.5
    assert default_summary.avg_latency_ms == 140.0
    assert default_summary.p95_latency_ms == 180.0

    no_rerank_summary = next(item for item in summary.mode_summaries if item.mode == BenchmarkMode.agentic_no_rerank)
    assert no_rerank_summary.correctness_rate == 1.0
    assert no_rerank_summary.avg_latency_ms == 260.0
    assert no_rerank_summary.p95_latency_ms == 260.0
