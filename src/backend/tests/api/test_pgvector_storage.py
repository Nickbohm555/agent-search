import os

import pytest
from sqlalchemy import create_engine, text

from main import app
from fastapi.testclient import TestClient
from services import wiki_ingestion_service


def _mock_wikipedia_loader(*_args, **_kwargs):
    long_content = " ".join(
        [
            "The Strait of Hormuz links the Persian Gulf with the Gulf of Oman and carries major energy shipments."
        ]
        * 30
    )
    return [
        type(
            "MockLoadedDocument",
            (),
            {
                "page_content": long_content,
                "metadata": {
                    "title": "Strait of Hormuz",
                    "source": "https://en.wikipedia.org/wiki/Strait_of_Hormuz",
                },
            },
        )()
    ]


@pytest.mark.smoke
def test_pgvector_extension_and_embedding_column_exist_on_postgres():
    database_url = os.getenv("DATABASE_URL", "")
    if "postgresql" not in database_url:
        pytest.skip("Postgres-backed smoke check requires a PostgreSQL DATABASE_URL")

    engine = create_engine(database_url, future=True)
    with engine.connect() as connection:
        extension_exists = connection.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"),
        ).scalar()
        assert extension_exists == 1

        embedding_column = connection.execute(
            text(
                """
                SELECT udt_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'internal_document_chunks'
                  AND column_name = 'embedding'
                """
            )
        ).scalar()
        assert embedding_column == "vector"


@pytest.mark.smoke
def test_wiki_load_vectorize_and_retrieve_path_on_postgres(monkeypatch: pytest.MonkeyPatch):
    """Exercise wiki load -> pgvector write -> retrieval in one deterministic smoke path."""
    database_url = os.getenv("DATABASE_URL", "")
    if "postgresql" not in database_url:
        pytest.skip("Postgres-backed smoke check requires a PostgreSQL DATABASE_URL")

    engine = create_engine(database_url, future=True)
    source_id = "strait_of_hormuz"
    monkeypatch.setattr(wiki_ingestion_service, "_load_wikipedia_documents", _mock_wikipedia_loader)

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    DELETE FROM internal_documents
                    WHERE source_ref = :source_ref
                    """
                ),
                {"source_ref": source_id},
            )
        with TestClient(app) as client:
            load_response = client.post(
                "/api/internal-data/load",
                json={
                    "source_type": "wiki",
                    "wiki": {
                        "source_id": source_id,
                    },
                },
            )
            assert load_response.status_code == 200
            load_data = load_response.json()
            assert load_data["status"] == "success"
            assert load_data["source_type"] == "wiki"
            assert load_data["documents_loaded"] >= 1
            assert load_data["chunks_created"] >= 1

            with engine.connect() as connection:
                vectorized_chunk_count = connection.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM internal_document_chunks chunks
                        JOIN internal_documents docs ON docs.id = chunks.document_id
                        WHERE docs.source_type = 'wiki'
                          AND docs.source_ref = :source_ref
                          AND chunks.embedding IS NOT NULL
                        """
                    ),
                    {"source_ref": source_id},
                ).scalar_one()

            assert vectorized_chunk_count >= 1

            retrieve_response = client.post(
                "/api/internal-data/retrieve",
                json={
                    "query": "Which waterway links the Persian Gulf and affects seaborne oil transit?",
                    "limit": 5,
                },
            )
            assert retrieve_response.status_code == 200
            retrieve_data = retrieve_response.json()
            assert len(retrieve_data["results"]) >= 1
            assert any(
                item["source_type"] == "wiki" and item["source_ref"] == source_id
                for item in retrieve_data["results"]
            )
    finally:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    DELETE FROM internal_documents
                    WHERE source_ref = :source_ref
                    """
                ),
                {"source_ref": source_id},
            )
