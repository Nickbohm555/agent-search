from __future__ import annotations

from urllib.parse import unquote, urlparse

from schemas import InternalDocumentInput, WikiLoadInput

_STRAIT_OF_HORMUZ_URL = "https://en.wikipedia.org/wiki/Strait_of_Hormuz"

_WIKI_FIXTURES: dict[str, dict[str, str]] = {
    "strait of hormuz": {
        "title": "Strait of Hormuz",
        "canonical_url": _STRAIT_OF_HORMUZ_URL,
        "content": (
            "The Strait of Hormuz is a narrow waterway connecting the Persian Gulf "
            "with the Gulf of Oman and the Arabian Sea. A substantial share of "
            "seaborne oil trade transits the strait, making it strategically "
            "important to global energy markets. Regional military tensions, "
            "shipping security incidents, and sanctions policy frequently affect "
            "risk assessments for transit through the corridor."
        ),
    }
}


def _normalize_topic(value: str) -> str:
    return value.strip().replace("_", " ").replace("-", " ").lower()


def _extract_topic_from_url(url: str) -> str:
    path = urlparse(url).path
    slug = path.rstrip("/").split("/")[-1]
    return _normalize_topic(unquote(slug))


def resolve_wiki_documents(wiki: WikiLoadInput) -> list[InternalDocumentInput]:
    """Resolve deterministic wiki-derived documents for scaffold ingestion.

    Called by `internal_data_service.load_internal_data` when a caller selects
    `source_type="wiki"`. This keeps CI deterministic by using local fixtures
    instead of live network fetches while preserving a wiki-oriented contract.
    """
    candidate_topics: list[str] = []
    if wiki.topic:
        candidate_topics.append(_normalize_topic(wiki.topic))
    if wiki.url:
        candidate_topics.append(_extract_topic_from_url(wiki.url))

    for topic in candidate_topics:
        fixture = _WIKI_FIXTURES.get(topic)
        if not fixture:
            continue
        return [
            InternalDocumentInput(
                title=fixture["title"],
                content=fixture["content"],
                source_ref=wiki.url or fixture["canonical_url"],
            )
        ]

    raise ValueError("Unsupported wiki source. Supported topic: Strait of Hormuz.")
