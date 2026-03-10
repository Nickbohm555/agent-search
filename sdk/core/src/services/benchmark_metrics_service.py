from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from models import BenchmarkQualityScore, BenchmarkResult

logger = logging.getLogger(__name__)

_DEFAULT_MIN_CORRECTNESS = 0.75
_DEFAULT_MAX_LATENCY_MS_P95 = 30000


@dataclass(frozen=True)
class BenchmarkThresholds:
    min_correctness: float
    max_latency_ms_p95: float


@dataclass(frozen=True)
class BenchmarkAggregateMetrics:
    completed_questions: int
    total_questions: int
    correctness_rate: float | None
    avg_latency_ms: float | None
    p95_latency_ms: float | None
    passed: bool


class BenchmarkMetricsService:
    """Computes deterministic benchmark metrics for run-level and mode-level summaries."""

    def thresholds_from_snapshot(self, snapshot: object) -> BenchmarkThresholds:
        if not isinstance(snapshot, dict):
            logger.warning("Benchmark metrics missing SLO snapshot; using defaults.")
            return BenchmarkThresholds(
                min_correctness=_DEFAULT_MIN_CORRECTNESS,
                max_latency_ms_p95=float(_DEFAULT_MAX_LATENCY_MS_P95),
            )

        min_correctness = self._coerce_float(snapshot.get("min_correctness"), default=_DEFAULT_MIN_CORRECTNESS)
        max_latency_ms_p95 = self._coerce_float(snapshot.get("max_latency_ms_p95"), default=_DEFAULT_MAX_LATENCY_MS_P95)
        logger.info(
            "Benchmark metrics thresholds resolved min_correctness=%.4f max_latency_ms_p95=%.2f",
            min_correctness,
            max_latency_ms_p95,
        )
        return BenchmarkThresholds(
            min_correctness=min_correctness,
            max_latency_ms_p95=max_latency_ms_p95,
        )

    def aggregate(
        self,
        *,
        result_rows: list[BenchmarkResult],
        quality_rows: list[BenchmarkQualityScore],
        thresholds: BenchmarkThresholds,
    ) -> BenchmarkAggregateMetrics:
        total_questions = len(result_rows)
        completed_questions = sum(1 for row in result_rows if row.execution_error is None)
        quality_by_key = {(row.mode, row.question_id): row for row in quality_rows}
        passed_quality_count = 0
        for row in result_rows:
            quality_row = quality_by_key.get((row.mode, row.question_id))
            if quality_row is not None and quality_row.passed is True:
                passed_quality_count += 1
        correctness_rate = (passed_quality_count / total_questions) if total_questions > 0 else None

        successful_latencies = [
            float(row.latency_ms)
            for row in result_rows
            if row.execution_error is None and isinstance(row.latency_ms, int) and row.latency_ms >= 0
        ]
        avg_latency_ms = (sum(successful_latencies) / len(successful_latencies)) if successful_latencies else None
        p95_latency_ms = self._percentile(successful_latencies, percentile=95.0) if successful_latencies else None

        passed = self._deterministic_pass_fail(
            correctness_rate=correctness_rate,
            p95_latency_ms=p95_latency_ms,
            thresholds=thresholds,
        )
        logger.info(
            "Benchmark metrics aggregated total=%s completed=%s passed_quality=%s correctness_rate=%s avg_latency_ms=%s p95_latency_ms=%s passed=%s",
            total_questions,
            completed_questions,
            passed_quality_count,
            correctness_rate,
            avg_latency_ms,
            p95_latency_ms,
            passed,
        )
        return BenchmarkAggregateMetrics(
            completed_questions=completed_questions,
            total_questions=total_questions,
            correctness_rate=correctness_rate,
            avg_latency_ms=avg_latency_ms,
            p95_latency_ms=p95_latency_ms,
            passed=passed,
        )

    @staticmethod
    def _coerce_float(raw: object, *, default: float) -> float:
        if isinstance(raw, (float, int)):
            return float(raw)
        return float(default)

    @staticmethod
    def _percentile(values: list[float], *, percentile: float) -> float:
        if not values:
            raise ValueError("Percentile requires at least one value.")
        sorted_values = sorted(values)
        rank = max(1, int(math.ceil((percentile / 100.0) * len(sorted_values))))
        index = min(len(sorted_values) - 1, rank - 1)
        return sorted_values[index]

    @staticmethod
    def _deterministic_pass_fail(
        *,
        correctness_rate: float | None,
        p95_latency_ms: float | None,
        thresholds: BenchmarkThresholds,
    ) -> bool:
        if correctness_rate is None or p95_latency_ms is None:
            return False
        return correctness_rate >= thresholds.min_correctness and p95_latency_ms <= thresholds.max_latency_ms_p95
