from fastapi import APIRouter

from schemas import HealthResponse
from services.health_service import get_health_status

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return get_health_status()
