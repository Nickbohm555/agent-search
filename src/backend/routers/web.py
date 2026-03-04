from fastapi import APIRouter

from schemas import (
    WebOpenUrlRequest,
    WebOpenUrlResponse,
    WebSearchRequest,
    WebSearchResponse,
)
from services.web_service import web_open_url, web_search

router = APIRouter(prefix="/api/web", tags=["web"])


@router.post("/search", response_model=WebSearchResponse)
def search_web(payload: WebSearchRequest) -> WebSearchResponse:
    return web_search(payload.query, payload.limit)


@router.post("/open-url", response_model=WebOpenUrlResponse)
def open_web_url(payload: WebOpenUrlRequest) -> WebOpenUrlResponse:
    return web_open_url(payload.url)
