from typing import Optional

from pydantic import BaseModel, Field


class WebSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=10)


class WebSearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class WebSearchResponse(BaseModel):
    query: str
    results: list[WebSearchResult]


class WebOpenUrlRequest(BaseModel):
    url: str = Field(min_length=1)


class WebOpenUrlResponse(BaseModel):
    title: str
    url: str
    content: str
    content_type: str = "text/plain"
    published_at: Optional[str] = None


class WebToolRun(BaseModel):
    sub_query: str
    search_results: list[WebSearchResult]
    opened_urls: list[str]
    opened_pages: list[WebOpenUrlResponse]
