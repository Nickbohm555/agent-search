import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from common.db import wipe_all_benchmark_data
from config import benchmarks_enabled
from db import get_db
from schemas import (
    BenchmarkMode,
    BenchmarkModeComparison,
    BenchmarkRunCancelResponse,
    BenchmarkRunCompareResponse,
    BenchmarkRunCreateRequest,
    BenchmarkRunCreateResponse,
    BenchmarkRunListResponse,
    BenchmarkRunStatusResponse,
    BenchmarkWipeResponse,
)
from services.benchmark_jobs import (
    cancel_benchmark_run,
    get_benchmark_run_status,
    list_benchmark_runs,
    start_benchmark_run_job,
)

logger = logging.getLogger(__name__)


def require_benchmarks_enabled() -> None:
    if benchmarks_enabled():
        return
    logger.warning("Benchmarks request blocked because BENCHMARKS_ENABLED=false")
    raise HTTPException(
        status_code=503,
        detail="Benchmarking is disabled. Set BENCHMARKS_ENABLED=true to enable benchmark endpoints.",
    )


router = APIRouter(
    prefix="/api/benchmarks",
    tags=["benchmarks"],
    dependencies=[Depends(require_benchmarks_enabled)],
)


@router.post("/runs", response_model=BenchmarkRunCreateResponse)
def create_benchmark_run(payload: BenchmarkRunCreateRequest) -> BenchmarkRunCreateResponse:
    logger.info(
        "Benchmarks router create requested dataset_id=%s mode_count=%s",
        payload.dataset_id,
        len(payload.modes),
    )
    return start_benchmark_run_job(payload)


@router.get("/runs", response_model=BenchmarkRunListResponse)
def list_runs(db: Session = Depends(get_db)) -> BenchmarkRunListResponse:
    logger.info("Benchmarks router list requested")
    return list_benchmark_runs(db=db)


@router.get("/runs/{run_id}", response_model=BenchmarkRunStatusResponse)
def get_run(run_id: str, db: Session = Depends(get_db)) -> BenchmarkRunStatusResponse:
    logger.info("Benchmarks router get requested run_id=%s", run_id)
    response = get_benchmark_run_status(run_id=run_id, db=db)
    if response is None:
        raise HTTPException(status_code=404, detail="Benchmark run not found.")
    return response


@router.post("/runs/{run_id}/cancel", response_model=BenchmarkRunCancelResponse)
def cancel_run(run_id: str, db: Session = Depends(get_db)) -> BenchmarkRunCancelResponse:
    logger.info("Benchmarks router cancel requested run_id=%s", run_id)
    cancelled = cancel_benchmark_run(run_id=run_id, db=db)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Benchmark run not found or already finished.")
    return BenchmarkRunCancelResponse(status="success", message="Cancellation requested.")


@router.get("/runs/{run_id}/compare", response_model=BenchmarkRunCompareResponse)
def compare_run_modes(run_id: str, db: Session = Depends(get_db)) -> BenchmarkRunCompareResponse:
    logger.info("Benchmarks router compare requested run_id=%s", run_id)
    response = get_benchmark_run_status(run_id=run_id, db=db)
    if response is None:
        raise HTTPException(status_code=404, detail="Benchmark run not found.")

    baseline_mode = BenchmarkMode.baseline_retrieve_then_answer
    baseline_summary = next((item for item in response.mode_summaries if item.mode == baseline_mode), None)
    if baseline_summary is None:
        logger.warning(
            "Benchmarks router compare failed baseline missing run_id=%s baseline_mode=%s",
            run_id,
            baseline_mode.value,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Baseline mode summary missing for run: {baseline_mode.value}",
        )

    def _compute_delta(value: float | None, baseline_value: float | None) -> float | None:
        if value is None or baseline_value is None:
            return None
        return value - baseline_value

    comparisons = [
        BenchmarkModeComparison(
            mode=summary.mode,
            correctness_rate=summary.correctness_rate,
            correctness_delta=_compute_delta(summary.correctness_rate, baseline_summary.correctness_rate),
            p95_latency_ms=summary.p95_latency_ms,
            p95_latency_delta_ms=_compute_delta(summary.p95_latency_ms, baseline_summary.p95_latency_ms),
        )
        for summary in response.mode_summaries
    ]
    logger.info(
        "Benchmarks router compare resolved run_id=%s baseline_mode=%s mode_count=%s",
        run_id,
        baseline_mode.value,
        len(comparisons),
    )
    return BenchmarkRunCompareResponse(
        run_id=run_id,
        baseline_mode=baseline_mode,
        comparisons=comparisons,
    )


@router.post("/wipe", response_model=BenchmarkWipeResponse)
def wipe_benchmark_data(db: Session = Depends(get_db)) -> BenchmarkWipeResponse:
    logger.info("Benchmarks router wipe requested")
    try:
        deleted_runs = wipe_all_benchmark_data(db)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Benchmarks router wipe failed")
        raise HTTPException(status_code=500, detail="Failed to wipe benchmark data.") from None

    logger.info("Benchmarks router wipe completed deleted_runs=%s", deleted_runs)
    return BenchmarkWipeResponse(
        status="success",
        message="All benchmark run data removed.",
        deleted_runs=deleted_runs,
    )
