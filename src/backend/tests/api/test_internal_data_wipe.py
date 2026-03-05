import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db import get_db
from routers.internal_data import router as internal_data_router


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def test_post_wipe_returns_success_and_empties_internal_tables() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    metadata = MetaData()
    documents = Table(
        "internal_documents",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String(255), nullable=False),
    )
    chunks = Table(
        "internal_document_chunks",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("document_id", Integer, ForeignKey("internal_documents.id"), nullable=False),
        Column("content", String, nullable=False),
    )
    metadata.create_all(engine)

    with Session(engine) as session:
        session.execute(documents.insert(), [{"id": 1, "title": "Doc 1"}])
        session.execute(chunks.insert(), [{"id": 1, "document_id": 1, "content": "Chunk 1"}])
        session.commit()

    app = FastAPI()
    app.include_router(internal_data_router)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.post("/api/internal-data/wipe")

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "All internal documents and chunks removed.",
    }

    with Session(engine) as session:
        remaining_documents = session.scalar(select(func.count()).select_from(documents))
        remaining_chunks = session.scalar(select(func.count()).select_from(chunks))

    assert remaining_documents == 0
    assert remaining_chunks == 0
