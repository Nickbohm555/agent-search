from __future__ import annotations

import logging
from typing import Any

from langchain_core.documents import Document
from langchain_core.tools import BaseTool, tool

logger = logging.getLogger(__name__)


def _format_results(results: list[Document]) -> str:
    if not results:
        return "No relevant documents found."

    lines: list[str] = []
    for index, result in enumerate(results, start=1):
        metadata = result.metadata or {}
        title = str(metadata.get("title") or metadata.get("wiki_page") or "Unknown title")
        source = str(metadata.get("source") or metadata.get("wiki_url") or "Unknown source")
        content = result.page_content.strip()
        lines.append(f"{index}. title={title} source={source} content={content}")
    return "\n".join(lines)


def make_retriever_tool(vector_store: Any) -> BaseTool:
    """Build a retriever tool over a vector store similarity search interface."""

    @tool
    def search_database(
        query: str,
        limit: int = 10,
        wiki_source_filter: str | None = None,
    ) -> str:
        """Search internal wiki data by semantic similarity.

        Args:
            query: Natural language question to search for.
            limit: Maximum number of matching chunks to return.
            wiki_source_filter: Optional wiki source identifier or URL to filter by metadata.source.
        """
        safe_limit = max(1, limit)
        filter_payload = {"source": wiki_source_filter} if wiki_source_filter else None
        results = vector_store.similarity_search(query, k=safe_limit, filter=filter_payload)
        logger.info(
            "Retriever tool search_database query=%r limit=%s filter=%s result_count=%s",
            query,
            safe_limit,
            filter_payload,
            len(results),
        )
        return _format_results(results)

    return search_database
