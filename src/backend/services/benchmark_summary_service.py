from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import BenchmarkQualityScore, BenchmarkResult, BenchmarkRun
from schemas import BenchmarkMode, BenchmarkModeSummary
from services.benchmark_metrics_service import BenchmarkAggregateMetrics, BenchmarkMetricsService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BenchmarkRunSummaryBundle:
    mode_summaries: list[BenchmarkModeSummary]
    mode_pass_fail: dict[str, bool]
    completed_questions: int
    total_questions: int
    run_correctness_rate: float | None
    run_avg_latency_ms: float | None
    run_p95_latency_ms: float | None
    run_passed: bool


class BenchmarkSummaryService:
    """Assembles mode-level and run-level benchmark summaries."""

    def __init__(self, *, metrics_service: BenchmarkMetricsService | None = None) -> None:
        self._metrics_service = metrics_service or BenchmarkMetricsService()

    def build_run_summary(
        self,
        *,
        db: Session,
        run: BenchmarkRun,
        parsed_modes: list[BenchmarkMode],
    ) -> BenchmarkRunSummaryBundle:
        result_rows = db.scalars(select(BenchmarkResult).where(BenchmarkResult.run_id == run.run_id)).all()
        quality_rows = db.scalars(select(BenchmarkQualityScore).where(BenchmarkQualityScore.run_id == run.run_id)).all()
        thresholds = self._metrics_service.thresholds_from_snapshot(run.slo_snapshot)

        run_metrics = self._metrics_service.aggregate(
            result_rows=result_rows,
            quality_rows=quality_rows,
            thresholds=thresholds,
        )

        mode_summaries: list[BenchmarkModeSummary] = []
        mode_pass_fail: dict[str, bool] = {}
        for mode in parsed_modes:
            mode_metrics = self._metrics_service.aggregate(
                result_rows=[row for row in result_rows if row.mode == mode.value],
                quality_rows=[row for row in quality_rows if row.mode == mode.value],
                thresholds=thresholds,
            )
            mode_summaries.append(self._build_mode_summary(mode=mode, metrics=mode_metrics))
            mode_pass_fail[mode.value] = mode_metrics.passed

        logger.info(
            "Benchmark summary assembled run_id=%s mode_count=%s run_passed=%s run_correctness_rate=%s run_p95_latency_ms=%s",
            run.run_id,
            len(mode_summaries),
            run_metrics.passed,
            run_metrics.correctness_rate,
            run_metrics.p95_latency_ms,
        )
        return BenchmarkRunSummaryBundle(
            mode_summaries=mode_summaries,
            mode_pass_fail=mode_pass_fail,
            completed_questions=run_metrics.completed_questions,
            total_questions=run_metrics.total_questions,
            run_correctness_rate=run_metrics.correctness_rate,
            run_avg_latency_ms=run_metrics.avg_latency_ms,
            run_p95_latency_ms=run_metrics.p95_latency_ms,
            run_passed=run_metrics.passed,
        )

    @staticmethod
    def _build_mode_summary(*, mode: BenchmarkMode, metrics: BenchmarkAggregateMetrics) -> BenchmarkModeSummary:
        return BenchmarkModeSummary(
            mode=mode,
            completed_questions=metrics.completed_questions,
            total_questions=metrics.total_questions,
            correctness_rate=metrics.correctness_rate,
            avg_latency_ms=metrics.avg_latency_ms,
            p95_latency_ms=metrics.p95_latency_ms,
        )
