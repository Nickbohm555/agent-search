import logging
import os
from typing import Callable, Optional

from sqlalchemy import Column, Integer, MetaData, String, Table, insert, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from common.db import wipe_all_internal_data
from db import DATABASE_URL
from schemas import (
    InternalDataLoadRequest,
    InternalDataLoadResponse,
    WikiLoadInput,
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


class InternalDataLoadCancelled(RuntimeError):
    pass

logger = logging.getLogger(__name__)

_VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")
_ALL_WIKI_SOURCE_ID = "all"

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
    loaded_source_ids = _get_loaded_wiki_source_ids(db)

    sources = list_wiki_sources()
    all_sources_loaded = len(loaded_source_ids) >= len(sources) and all(
        source.source_id in loaded_source_ids for source in sources
    )

    options = [
        WikiSourceOption(
            source_id=_ALL_WIKI_SOURCE_ID,
            label="All Sources",
            article_query="All sources",
            already_loaded=all_sources_loaded,
        ),
        *[
            WikiSourceOption(
                source_id=source.source_id,
                label=source.label,
                article_query=source.article_query,
                already_loaded=source.source_id in loaded_source_ids,
            )
            for source in sources
        ],
    ]
    logger.info(
        "Listed %s wiki sources; %s marked as loaded.",
        len(options),
        len(loaded_source_ids),
    )
    return WikiSourcesResponse(sources=options)


def load_internal_data(
    payload: InternalDataLoadRequest,
    db: Session,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
    cancel_cb: Optional[Callable[[], bool]] = None,
) -> InternalDataLoadResponse:
    """Load curated wiki source documents, chunk them, and store in PGVector."""
    if payload.source_type != "wiki" or payload.wiki is None:
        raise ValueError("Only wiki source_type is supported for internal data load.")

    def report(completed: int, total: int, message: str) -> None:
        if progress_cb:
            progress_cb(completed, total, message)

    def check_cancelled() -> None:
        if cancel_cb and cancel_cb():
            raise InternalDataLoadCancelled("Internal data load cancelled.")

    vector_store = get_vector_store(
        connection=DATABASE_URL,
        collection_name=_VECTOR_COLLECTION_NAME,
        embeddings=get_embedding_model(),
    )

    if payload.wiki.source_id.strip() == _ALL_WIKI_SOURCE_ID:
        loaded_source_ids = _get_loaded_wiki_source_ids(db)
        sources = [source for source in list_wiki_sources() if source.source_id not in loaded_source_ids]

        if not sources:
            report(1, 1, "All sources already loaded.")
            return InternalDataLoadResponse(
                status="success",
                source_type=payload.source_type,
                documents_loaded=0,
                chunks_created=0,
            )

        total_units = len(sources) * 2 + 2
        completed_units = 0
        per_source_documents: list[tuple[object, list]] = []
        all_documents = []
        all_chunks = []
        for source in sources:
            check_cancelled()
            wiki_documents = resolve_wiki_documents(WikiLoadInput(source_id=source.source_id))
            per_source_documents.append((source, wiki_documents))
            all_documents.extend(wiki_documents)
            completed_units += 1
            report(completed_units, total_units, f"Loaded source {source.label}.")

        for source, wiki_documents in per_source_documents:
            check_cancelled()
            chunked_documents = chunk_wiki_documents(wiki_documents)
            all_chunks.extend(chunked_documents)
            completed_units += 1
            report(completed_units, total_units, f"Chunked source {source.label}.")

        check_cancelled()
        vector_ids = add_documents_to_store(vector_store, all_chunks)
        completed_units += 1
        report(completed_units, total_units, "Stored vectors.")

        insert_rows = []
        for source, wiki_documents in per_source_documents:
            for document in wiki_documents:
                insert_rows.append(
                    {
                        "source_type": "wiki",
                        "source_ref": source.source_id,
                        "title": str((document.metadata or {}).get("title") or source.label).strip() or source.label,
                        "content": document.page_content,
                    },
                )

        check_cancelled()
        db.execute(insert(_internal_documents), insert_rows)
        db.commit()
        completed_units += 1
        report(completed_units, total_units, "Inserted metadata.")

        logger.info(
            "Loaded all wiki sources: sources=%s documents=%s chunks=%s vector_ids=%s",
            len(sources),
            len(all_documents),
            len(chunked_documents),
            len(vector_ids),
        )

        return InternalDataLoadResponse(
            status="success",
            source_type=payload.source_type,
            documents_loaded=len(all_documents),
            chunks_created=len(all_chunks),
        )

    source = resolve_wiki_source(payload.wiki.source_id)
    total_units = 4
    completed_units = 0
    report(completed_units, total_units, f"Starting {source.label}.")
    check_cancelled()
    wiki_documents = resolve_wiki_documents(WikiLoadInput(source_id=source.source_id))
    completed_units += 1
    report(completed_units, total_units, "Loaded document.")
    check_cancelled()
    chunked_documents = chunk_wiki_documents(wiki_documents)
    completed_units += 1
    report(completed_units, total_units, "Chunked document.")
    check_cancelled()
    vector_ids = add_documents_to_store(vector_store, chunked_documents)
    completed_units += 1
    report(completed_units, total_units, "Stored vectors.")
    check_cancelled()

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
    completed_units += 1
    report(completed_units, total_units, "Inserted metadata.")

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


def _get_loaded_wiki_source_ids(db: Session) -> set[str]:
    try:
        return {
            source_id
            for source_id in db.execute(
                select(_internal_documents.c.source_ref).where(
                    _internal_documents.c.source_type == "wiki",
                    _internal_documents.c.source_ref.is_not(None),
                ),
            ).scalars()
            if source_id
        }
    except ProgrammingError as exc:
        if "UndefinedTable" in str(exc):
            logger.warning("Internal documents table missing; assuming no loaded wiki sources.")
            return set()
        raise
