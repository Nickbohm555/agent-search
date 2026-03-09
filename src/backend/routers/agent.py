from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from schemas import (
    RuntimeAgentRunAsyncCancelResponse,
    RuntimeAgentRunAsyncStartResponse,
    RuntimeAgentRunAsyncStatusResponse,
    RuntimeAgentRunRequest,
    RuntimeAgentRunResponse,
)
from services.agent_jobs import cancel_agent_run_job, get_agent_run_job, start_agent_run_job
from services.agent_service import run_runtime_agent

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/run", response_model=RuntimeAgentRunResponse)
def runtime_agent_run(
    payload: RuntimeAgentRunRequest,
    db: Session = Depends(get_db),
) -> RuntimeAgentRunResponse:
    return run_runtime_agent(payload, db=db)


@router.post("/run-async", response_model=RuntimeAgentRunAsyncStartResponse)
def runtime_agent_run_async(payload: RuntimeAgentRunRequest) -> RuntimeAgentRunAsyncStartResponse:
    job = start_agent_run_job(payload)
    return RuntimeAgentRunAsyncStartResponse(job_id=job.job_id, run_id=job.run_id, status=job.status)


@router.get("/run-status/{job_id}", response_model=RuntimeAgentRunAsyncStatusResponse)
def runtime_agent_run_status(job_id: str) -> RuntimeAgentRunAsyncStatusResponse:
    job = get_agent_run_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return RuntimeAgentRunAsyncStatusResponse(
        job_id=job.job_id,
        run_id=job.run_id,
        status=job.status,
        message=job.message,
        stage=job.stage,
        stages=list(job.stages),
        decomposition_sub_questions=list(job.decomposition_sub_questions),
        sub_qa=[item.model_copy(deep=True) for item in job.sub_qa],
        output=job.output,
        result=job.result.model_copy(deep=True) if job.result is not None else None,
        error=job.error,
        cancel_requested=job.cancel_requested,
    )


@router.post("/run-cancel/{job_id}", response_model=RuntimeAgentRunAsyncCancelResponse)
def runtime_agent_run_cancel(job_id: str) -> RuntimeAgentRunAsyncCancelResponse:
    cancelled = cancel_agent_run_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Job not found or already finished.")
    return RuntimeAgentRunAsyncCancelResponse(status="success", message="Cancellation requested.")
