from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import get_db
from schemas import (
    InternalDataLoadRequest,
    InternalDataLoadResponse,
    InternalDataRetrieveRequest,
    InternalDataRetrieveResponse,
    WikiSourcesResponse,
)
from services.internal_data_service import (
    list_wiki_sources_with_load_state,
    load_internal_data,
    retrieve_internal_data,
)

router = APIRouter(prefix="/api/internal-data", tags=["internal-data"])


@router.post("/load", response_model=InternalDataLoadResponse)
def load_data(payload: InternalDataLoadRequest, db: Session = Depends(get_db)) -> InternalDataLoadResponse:
    """Load internal data from inline docs or deterministic wiki source."""
    try:
        return load_internal_data(payload, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/wiki-sources", response_model=WikiSourcesResponse)
def list_wiki_sources(db: Session = Depends(get_db)) -> WikiSourcesResponse:
    """Return curated wiki source options with already-loaded state for the UI."""
    return list_wiki_sources_with_load_state(db)


@router.post("/retrieve", response_model=InternalDataRetrieveResponse)
def retrieve_data(
    payload: InternalDataRetrieveRequest,
    db: Session = Depends(get_db),
) -> InternalDataRetrieveResponse:
    return retrieve_internal_data(payload, db)
