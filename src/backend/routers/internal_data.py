from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from schemas import (
    InternalDataLoadRequest,
    InternalDataLoadResponse,
    InternalDataRetrieveRequest,
    InternalDataRetrieveResponse,
)
from services.internal_data_service import load_internal_data, retrieve_internal_data

router = APIRouter(prefix="/api/internal-data", tags=["internal-data"])


@router.post("/load", response_model=InternalDataLoadResponse)
def load_data(payload: InternalDataLoadRequest, db: Session = Depends(get_db)) -> InternalDataLoadResponse:
    """Load internal data from inline docs or deterministic wiki source."""
    try:
        return load_internal_data(payload, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/retrieve", response_model=InternalDataRetrieveResponse)
def retrieve_data(
    payload: InternalDataRetrieveRequest,
    db: Session = Depends(get_db),
) -> InternalDataRetrieveResponse:
    return retrieve_internal_data(payload, db)
