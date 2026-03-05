import logging
import sys
from pathlib import Path

from sqlalchemy import Column, ForeignKey, Integer, String, Table, create_engine, event, func, select
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from common.db import wipe_all_internal_data
from db import Base


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def test_wipe_all_internal_data_deletes_chunks_then_documents_and_logs(caplog) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)

    documents = Table(
        "internal_documents",
        Base.metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String(255), nullable=False),
    )
    chunks = Table(
        "internal_document_chunks",
        Base.metadata,
        Column("id", Integer, primary_key=True),
        Column("document_id", Integer, ForeignKey("internal_documents.id"), nullable=False),
        Column("content", String, nullable=False),
    )
    Base.metadata.create_all(engine, tables=[documents, chunks])

    with Session(engine) as session:
        session.execute(
            documents.insert(),
            [{"id": 1, "title": "Doc 1"}, {"id": 2, "title": "Doc 2"}],
        )
        session.execute(
            chunks.insert(),
            [
                {"id": 1, "document_id": 1, "content": "Chunk 1"},
                {"id": 2, "document_id": 1, "content": "Chunk 2"},
                {"id": 3, "document_id": 2, "content": "Chunk 3"},
            ],
        )
        session.commit()

        with caplog.at_level(logging.INFO):
            wipe_all_internal_data(session)
        session.commit()

        remaining_documents = session.scalar(select(func.count()).select_from(documents))
        remaining_chunks = session.scalar(select(func.count()).select_from(chunks))

        assert remaining_documents == 0
        assert remaining_chunks == 0
        assert "Wiped internal data: deleted 3 chunk rows and 2 document rows." in caplog.text
