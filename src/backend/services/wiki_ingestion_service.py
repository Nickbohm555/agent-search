from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document

from schemas import WikiLoadInput

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WikiSourceDefinition:
    source_id: str
    label: str
    article_query: str


_WIKI_SOURCE_DEFINITIONS: tuple[WikiSourceDefinition, ...] = (
    WikiSourceDefinition("geopolitics", "Geopolitics", "Geopolitics"),
    WikiSourceDefinition("strait_of_hormuz", "Strait of Hormuz", "Strait of Hormuz"),
    WikiSourceDefinition("nato", "NATO", "NATO"),
    WikiSourceDefinition("european_union", "European Union", "European Union"),
    WikiSourceDefinition("united_nations", "United Nations", "United Nations"),
    WikiSourceDefinition(
        "foreign_policy_us",
        "Foreign Policy of the United States",
        "Foreign policy of the United States",
    ),
    WikiSourceDefinition("middle_east", "Middle East", "Middle East"),
    WikiSourceDefinition("cold_war", "Cold War", "Cold War"),
    WikiSourceDefinition("international_relations", "International Relations", "International relations"),
    WikiSourceDefinition(
        "balance_of_power",
        "Balance of Power (IR)",
        "Balance of power (international relations)",
    ),
)
_WIKI_SOURCES_BY_ID = {item.source_id: item for item in _WIKI_SOURCE_DEFINITIONS}
_MIN_WIKI_CHARS = 1000
_WIKI_DOC_CHARS_MAX = 8000


def list_wiki_sources() -> tuple[WikiSourceDefinition, ...]:
    """Return curated wiki-source definitions for load-time selection."""
    return _WIKI_SOURCE_DEFINITIONS


def resolve_wiki_source(source_id: str) -> WikiSourceDefinition:
    """Resolve one curated wiki source identifier or raise a validation error."""
    source = _WIKI_SOURCES_BY_ID.get(source_id.strip())
    if source is None:
        raise ValueError(f"Unsupported wiki source_id '{source_id}'.")
    return source


def _load_wikipedia_documents(article_query: str) -> list[Any]:
    """Load wiki content with LangChain `WikipediaLoader`.

    Called by `resolve_wiki_documents` for production wiki loads. Import remains
    local so tests can monkeypatch this function without requiring network calls.
    """
    try:
        from langchain_community.document_loaders import WikipediaLoader
    except ImportError as exc:
        raise ValueError("langchain_community is required for wiki loads.") from exc

    loader = WikipediaLoader(
        query=article_query,
        load_max_docs=1,
        doc_content_chars_max=_WIKI_DOC_CHARS_MAX,
        load_all_available_meta=True,
    )
    return loader.load()


def resolve_wiki_documents(wiki: WikiLoadInput) -> list[Document]:
    """Resolve wiki source content into normalized LangChain `Document` objects.

    Called by `internal_data_service.load_internal_data` when
    `source_type='wiki'`. This enforces curated source IDs and large-content
    requirements while preserving and normalizing attribution metadata.
    """
    source = resolve_wiki_source(wiki.source_id)
    loaded_documents = _load_wikipedia_documents(source.article_query)
    resolved_documents: list[Document] = []
    total_chars = 0
    metadata_keys: set[str] = set()

    for loaded in loaded_documents:
        content = str(getattr(loaded, "page_content", "")).strip()
        if not content:
            continue
        metadata = getattr(loaded, "metadata", {}) or {}
        title = str(metadata.get("title") or source.label).strip()
        source_ref = str(metadata.get("source") or source.source_id).strip() or source.source_id
        normalized_metadata = dict(metadata)
        normalized_metadata["source"] = source_ref
        normalized_metadata["title"] = title
        metadata_keys.update(str(key) for key in normalized_metadata.keys())
        total_chars += len(content)
        resolved_documents.append(
            Document(
                page_content=content,
                metadata=normalized_metadata,
            ),
        )

    if not resolved_documents:
        raise ValueError(f"No wiki content loaded for source_id '{source.source_id}'.")
    if total_chars < _MIN_WIKI_CHARS:
        raise ValueError(
            f"Loaded wiki content too small ({total_chars} chars). Minimum required is {_MIN_WIKI_CHARS}.",
        )

    logger.info(
        "Resolved %s wiki documents for source_id='%s' with metadata_keys=%s",
        len(resolved_documents),
        source.source_id,
        sorted(metadata_keys),
    )

    return resolved_documents
