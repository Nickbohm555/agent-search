from fastapi import APIRouter

from schemas import SearchSkeletonResponse
from services.search_service import get_search_scaffold

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search-skeleton", response_model=SearchSkeletonResponse)
def search_skeleton() -> SearchSkeletonResponse:
    return get_search_scaffold()
