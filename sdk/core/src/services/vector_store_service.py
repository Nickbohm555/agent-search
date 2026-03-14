from __future__ import annotations

import logging
from typing import Any

from langchain_community.vectorstores.pgvector import PGVector, _get_embedding_collection_store
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

CITATION_TITLE_METADATA_KEY = "citation_title"
CITATION_SOURCE_METADATA_KEY = "citation_source"
CITATION_DOCUMENT_ID_METADATA_KEY = "document_id"


def _collection_exists(connection: str, collection_name: str, use_jsonb: bool = True) -> bool:
    """Check whether the target PGVector collection already exists."""
    _, collection_store = _get_embedding_collection_store(None, use_jsonb=use_jsonb)
    engine = create_engine(connection, future=True)
    try:
        inspector = inspect(engine)
        if not inspector.has_table(collection_store.__tablename__):
            return False
        with Session(engine) as session:
            return collection_store.get_by_name(session, collection_name) is not None
    finally:
        engine.dispose()


def get_vector_store(connection: str, collection_name: str, embeddings: Embeddings) -> PGVector:
    """Create or fetch a single PGVector collection for app use."""
    existed_before = _collection_exists(connection=connection, collection_name=collection_name, use_jsonb=True)
    vector_store = PGVector(
        connection_string=connection,
        embedding_function=embeddings,
        collection_name=collection_name,
        use_jsonb=True,
    )
    logger.info(
        "PGVector collection ready: collection_name='%s' state=%s",
        collection_name,
        "existing" if existed_before else "created",
    )
    return vector_store


def _normalize_document_metadata(document: Document) -> Document:
    """Keep only required citation metadata fields for retrieval/filtering."""
    metadata = document.metadata or {}
    topic = str(metadata.get("title") or metadata.get("wiki_page") or "").strip()
    wiki_url = str(metadata.get("source") or metadata.get("wiki_url") or "").strip()
    document_id = str(metadata.get(CITATION_DOCUMENT_ID_METADATA_KEY) or document.id or "").strip()
    # Preserve explicit citation keys and legacy wiki keys for non-citation consumers.
    slim_metadata = {
        CITATION_TITLE_METADATA_KEY: topic,
        CITATION_SOURCE_METADATA_KEY: wiki_url,
        CITATION_DOCUMENT_ID_METADATA_KEY: document_id,
        "topic": topic,
        "wiki_url": wiki_url,
        "wiki_page": topic,
    }
    return Document(page_content=document.page_content, metadata=slim_metadata, id=document.id)


def add_documents_to_store(vector_store: PGVector, documents: list[Document]) -> list[str]:
    """Add documents to PGVector and return generated IDs."""
    if not documents:
        logger.info("No documents provided; skipping PGVector add.")
        return []

    normalized_documents = [_normalize_document_metadata(document) for document in documents]
    ids = vector_store.add_documents(normalized_documents)
    logger.info(
        "Added %s documents to PGVector collection='%s'",
        len(ids),
        vector_store.collection_name,
    )
    return ids


def search_documents_for_context(
    vector_store: Any,
    query: str,
    *,
    k: int,
    score_threshold: float | None = None,
) -> list[Document]:
    """Run one retrieval pass for context gathering before decomposition."""
    safe_k = max(1, k)
    if score_threshold is not None and hasattr(vector_store, "similarity_search_with_relevance_scores"):
        docs_with_scores = vector_store.similarity_search_with_relevance_scores(
            query,
            k=safe_k,
            score_threshold=score_threshold,
        )
        documents: list[Document] = []
        for doc, score in docs_with_scores:
            metadata = dict(doc.metadata or {})
            metadata["score"] = score
            documents.append(Document(page_content=doc.page_content, metadata=metadata, id=doc.id))
        logger.info(
            "Context search complete query=%r k=%s score_threshold=%s results=%s mode=with_scores",
            query,
            safe_k,
            score_threshold,
            len(documents),
        )
        return documents

    documents = vector_store.similarity_search(query, k=safe_k)
    logger.info(
        "Context search complete query=%r k=%s score_threshold=%s results=%s mode=similarity_search",
        query,
        safe_k,
        score_threshold,
        len(documents),
    )
    return documents


def search_documents_for_queries(
    vector_store: Any,
    queries: list[str],
    *,
    k: int,
    score_threshold: float | None = None,
) -> dict[str, list[Document]]:
    """Run retrieval for each query and return results keyed by query text."""
    results: dict[str, list[Document]] = {}
    safe_queries = [query.strip() for query in queries if isinstance(query, str) and query.strip()]
    logger.info(
        "Multi-query context search start query_count=%s k=%s score_threshold=%s",
        len(safe_queries),
        max(1, k),
        score_threshold,
    )
    for query in safe_queries:
        documents = search_documents_for_context(
            vector_store=vector_store,
            query=query,
            k=k,
            score_threshold=score_threshold,
        )
        results[query] = documents
    logger.info(
        "Multi-query context search complete query_count=%s total_results=%s",
        len(safe_queries),
        sum(len(docs) for docs in results.values()),
    )
    return results


def build_initial_search_context(documents: list[Document]) -> list[dict[str, str | int]]:
    """Return bounded, structured context items for coordinator decomposition input."""
    context_items: list[dict[str, str | int]] = []
    for rank, document in enumerate(documents, start=1):
        metadata = document.metadata or {}
        snippet = document.page_content.strip().replace("\n", " ")
        context_items.append(
            {
                "rank": rank,
                "document_id": str(metadata.get(CITATION_DOCUMENT_ID_METADATA_KEY) or document.id or ""),
                "title": str(metadata.get(CITATION_TITLE_METADATA_KEY) or ""),
                "source": str(metadata.get(CITATION_SOURCE_METADATA_KEY) or ""),
                "snippet": snippet[:250],
            }
        )
    return context_items
