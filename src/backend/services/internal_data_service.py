import logging
import os

from sqlalchemy import Column, Integer, MetaData, String, Table, insert, select
from sqlalchemy.orm import Session

from common.db import wipe_all_internal_data
from db import DATABASE_URL
from schemas import (
    InternalDataLoadRequest,
    InternalDataLoadResponse,
    WikiSourceOption,
    WikiSourcesResponse,
)
from services.vector_store_service import add_documents_to_store, get_vector_store
from services.wiki_ingestion_service import (
    chunk_wiki_documents,
    list_wiki_sources,
    resolve_wiki_documents,
    resolve_wiki_source,
)
from utils.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

_VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")

_metadata = MetaData()
_internal_documents = Table(
    "internal_documents",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("source_type", String(50), nullable=False),
    Column("source_ref", String(255), nullable=True),
    Column("title", String(255), nullable=False),
    Column("content", String, nullable=False),
)


def wipe_internal_data(db: Session) -> None:
    """Wipe internal documents/chunks via shared DB helper."""
    wipe_all_internal_data(db)
    db.commit()
    logger.info("Internal data wipe committed.")


def list_wiki_sources_with_load_state(db: Session) -> WikiSourcesResponse:
    """Return curated wiki sources with loaded state inferred from DB markers."""
    loaded_source_ids = {
        source_id
        for source_id in db.execute(
            select(_internal_documents.c.source_ref).where(
                _internal_documents.c.source_type == "wiki",
                _internal_documents.c.source_ref.is_not(None),
            ),
        ).scalars()
        if source_id
    }

    options = [
        WikiSourceOption(
            source_id=source.source_id,
            label=source.label,
            article_query=source.article_query,
            already_loaded=source.source_id in loaded_source_ids,
        )
        for source in list_wiki_sources()
    ]
    logger.info(
        "Listed %s wiki sources; %s marked as loaded.",
        len(options),
        len(loaded_source_ids),
    )
    return WikiSourcesResponse(sources=options)


def load_internal_data(payload: InternalDataLoadRequest, db: Session) -> InternalDataLoadResponse:
    """Load curated wiki source documents, chunk them, and store in PGVector."""
    if payload.source_type != "wiki" or payload.wiki is None:
        raise ValueError("Only wiki source_type is supported for internal data load.")

    source = resolve_wiki_source(payload.wiki.source_id)
    wiki_documents = resolve_wiki_documents(payload.wiki)
    chunked_documents = chunk_wiki_documents(wiki_documents)

    vector_store = get_vector_store(
        connection=DATABASE_URL,
        collection_name=_VECTOR_COLLECTION_NAME,
        embeddings=get_embedding_model(),
    )
    vector_ids = add_documents_to_store(vector_store, chunked_documents)

    db.execute(
        insert(_internal_documents),
        [
            {
                "source_type": "wiki",
                "source_ref": source.source_id,
                "title": str((document.metadata or {}).get("title") or source.label).strip() or source.label,
                "content": document.page_content,
            }
            for document in wiki_documents
        ],
    )

    db.commit()
    logger.info(
        "Loaded wiki source_id='%s': documents=%s chunks=%s vector_ids=%s",
        source.source_id,
        len(wiki_documents),
        len(chunked_documents),
        len(vector_ids),
    )

    return InternalDataLoadResponse(
        status="success",
        source_type=payload.source_type,
        documents_loaded=len(wiki_documents),
        chunks_created=len(chunked_documents),
    )
