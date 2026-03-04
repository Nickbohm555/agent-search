from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException

from schemas import WebOpenUrlResponse, WebSearchResponse, WebSearchResult, WebToolRun


@dataclass(frozen=True)
class _WebDocument:
    title: str
    url: str
    snippet: str
    content: str
    published_at: Optional[str] = None


_WEB_DOCUMENTS: tuple[_WebDocument, ...] = (
    _WebDocument(
        title="Competitor Z Announces Spring 2026 Product Launch",
        url="https://example.com/news/competitor-z-spring-2026-launch",
        snippet="Competitor Z shared launch timelines, pricing, and availability windows.",
        content=(
            "Competitor Z confirmed a Spring 2026 rollout with phased availability in North "
            "America and Europe. The release includes pricing tiers and migration guidance."
        ),
        published_at="2026-02-15",
    ),
    _WebDocument(
        title="Public Benchmark Report: AI Search UX Patterns",
        url="https://example.com/reports/ai-search-ux-patterns-2026",
        snippet="A public report comparing retrieval UX and query decomposition behavior.",
        content=(
            "The report compares response quality across retrieval stacks and highlights "
            "search-then-read behavior where agents open selected pages after ranking links."
        ),
        published_at="2026-01-10",
    ),
    _WebDocument(
        title="Industry Briefing: Agent Tooling Updates",
        url="https://example.com/briefing/agent-tooling-updates",
        snippet="Weekly roundup of web-search tooling and evaluation updates.",
        content=(
            "This briefing summarizes notable updates in agent tooling, including web search "
            "connector improvements and deterministic test harness recommendations."
        ),
        published_at="2026-03-01",
    ),
)


def _score_document(query: str, doc: _WebDocument) -> int:
    query_terms = {term for term in query.lower().split() if term}
    haystack = f"{doc.title} {doc.snippet} {doc.content}".lower()
    return sum(1 for term in query_terms if term in haystack)


def web_search(query: str, limit: int = 5) -> WebSearchResponse:
    ranked = sorted(
        _WEB_DOCUMENTS,
        key=lambda doc: (_score_document(query, doc), doc.url),
        reverse=True,
    )

    results = [
        WebSearchResult(title=doc.title, url=doc.url, snippet=doc.snippet)
        for doc in ranked[:limit]
    ]
    return WebSearchResponse(query=query, results=results)


def web_open_url(url: str) -> WebOpenUrlResponse:
    for doc in _WEB_DOCUMENTS:
        if doc.url == url:
            return WebOpenUrlResponse(
                title=doc.title,
                url=doc.url,
                content=doc.content,
                published_at=doc.published_at,
            )
    raise HTTPException(status_code=404, detail="URL not found in web corpus")


def run_web_search_then_open(
    sub_query: str,
    search_limit: int = 5,
    open_limit: int = 1,
) -> WebToolRun:
    search_response = web_search(sub_query, limit=search_limit)
    urls_to_open = [result.url for result in search_response.results[:open_limit]]
    opened_pages = [web_open_url(url) for url in urls_to_open]

    return WebToolRun(
        sub_query=sub_query,
        search_results=search_response.results,
        opened_urls=urls_to_open,
        opened_pages=opened_pages,
    )
