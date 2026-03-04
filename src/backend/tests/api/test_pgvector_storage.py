import os

import pytest
from sqlalchemy import create_engine, text


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
