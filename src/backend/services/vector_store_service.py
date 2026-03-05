from __future__ import annotations

import logging

from langchain_community.vectorstores.pgvector import PGVector, _get_embedding_collection_store
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


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
    """Ensure required wiki metadata fields are present for retrieval/filtering."""
    metadata = dict(document.metadata or {})
    metadata["wiki_page"] = str(metadata.get("wiki_page") or metadata.get("title") or "").strip()
    metadata["wiki_url"] = str(metadata.get("wiki_url") or metadata.get("source") or "").strip()
    return Document(page_content=document.page_content, metadata=metadata, id=document.id)


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
