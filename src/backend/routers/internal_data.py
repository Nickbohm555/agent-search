from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from schemas import (
    InternalDataLoadRequest,
    InternalDataLoadResponse,
    InternalDataLoadJobCancelResponse,
    InternalDataLoadJobStartResponse,
    InternalDataLoadJobStatusResponse,
    WipeResponse,
    WikiSourcesResponse,
)
from services.internal_data_jobs import (
    cancel_internal_data_job,
    get_internal_data_job,
    start_internal_data_job,
)
from services.internal_data_service import (
    list_wiki_sources_with_load_state,
    load_internal_data,
    wipe_internal_data,
)

router = APIRouter(prefix="/api/internal-data", tags=["internal-data"])


@router.post("/load", response_model=InternalDataLoadResponse)
def load_data(payload: InternalDataLoadRequest, db: Session = Depends(get_db)) -> InternalDataLoadResponse:
    """Load internal data from deterministic wiki source."""
    try:
        return load_internal_data(payload, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/load-async", response_model=InternalDataLoadJobStartResponse)
def load_data_async(payload: InternalDataLoadRequest) -> InternalDataLoadJobStartResponse:
    """Start async load of internal data and return job id."""
    job = start_internal_data_job(payload)
    return InternalDataLoadJobStartResponse(job_id=job.job_id, status=job.status)


@router.get("/load-status/{job_id}", response_model=InternalDataLoadJobStatusResponse)
def load_status(job_id: str) -> InternalDataLoadJobStatusResponse:
    """Get load job status/progress."""
    job = get_internal_data_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return InternalDataLoadJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        total=job.total,
        completed=job.completed,
        message=job.message,
        error=job.error,
        response=job.response,
    )


@router.post("/load-cancel/{job_id}", response_model=InternalDataLoadJobCancelResponse)
def load_cancel(job_id: str) -> InternalDataLoadJobCancelResponse:
    """Cancel a running load job."""
    cancelled = cancel_internal_data_job(job_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Job not found or already finished.")
    return InternalDataLoadJobCancelResponse(status="success", message="Cancellation requested.")


@router.post("/wipe", response_model=WipeResponse)
def wipe_data(db: Session = Depends(get_db)) -> WipeResponse:
    """Wipe all internal documents and chunks."""
    wipe_internal_data(db)
    return WipeResponse(status="success", message="All internal documents and chunks removed.")


@router.get("/wiki-sources", response_model=WikiSourcesResponse)
def list_wiki_sources(db: Session = Depends(get_db)) -> WikiSourcesResponse:
    """Return curated wiki source options with loaded state for the UI."""
    return list_wiki_sources_with_load_state(db)
