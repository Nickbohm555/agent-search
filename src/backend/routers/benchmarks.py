import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from schemas import (
    BenchmarkRunCancelResponse,
    BenchmarkRunCreateRequest,
    BenchmarkRunCreateResponse,
    BenchmarkRunListResponse,
    BenchmarkRunStatusResponse,
)
from services.benchmark_jobs import (
    cancel_benchmark_run,
    get_benchmark_run_status,
    list_benchmark_runs,
    start_benchmark_run_job,
)

router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])
logger = logging.getLogger(__name__)


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
