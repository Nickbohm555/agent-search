import logging

from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table, delete
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_metadata = MetaData()
_internal_documents = Table(
    "internal_documents",
    _metadata,
    Column("id", Integer, primary_key=True),
)
_internal_document_chunks = Table(
    "internal_document_chunks",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("document_id", Integer, ForeignKey("internal_documents.id"), nullable=False),
)


def wipe_all_internal_data(session: Session) -> None:
    """Delete internal chunks first, then internal documents."""
    chunk_result = session.execute(delete(_internal_document_chunks))
    document_result = session.execute(delete(_internal_documents))
    session.flush()

    chunks_deleted = chunk_result.rowcount if chunk_result.rowcount is not None else 0
    documents_deleted = document_result.rowcount if document_result.rowcount is not None else 0
    logger.info(
        "Wiped internal data: deleted %s chunk rows and %s document rows.",
        chunks_deleted,
        documents_deleted,
    )

