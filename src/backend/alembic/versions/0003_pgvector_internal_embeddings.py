"""migrate internal chunk embeddings to pgvector

Revision ID: 0003_pgvector_embed
Revises: 0002_internal_data_tables
Create Date: 2026-03-04 02:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "0003_pgvector_embed"
down_revision: Union[str, None] = "0002_internal_data_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "internal_document_chunks",
        sa.Column("embedding_vector", Vector(16), nullable=True),
    )

    op.execute(
        """
        UPDATE internal_document_chunks
        SET embedding_vector = embedding_json::vector
        WHERE embedding_json IS NOT NULL
        """
    )

    op.alter_column(
        "internal_document_chunks",
        "embedding_vector",
        existing_type=Vector(16),
        nullable=False,
    )

    op.create_index(
        "ix_internal_document_chunks_embedding_vector_ivfflat",
        "internal_document_chunks",
        ["embedding_vector"],
        postgresql_using="ivfflat",
        postgresql_ops={"embedding_vector": "vector_cosine_ops"},
    )

    op.drop_column("internal_document_chunks", "embedding_json")


def downgrade() -> None:
    op.add_column(
        "internal_document_chunks",
        sa.Column("embedding_json", sa.Text(), nullable=True),
    )

    op.execute(
        """
        UPDATE internal_document_chunks
        SET embedding_json = embedding_vector::text
        WHERE embedding_vector IS NOT NULL
        """
    )

    op.alter_column(
        "internal_document_chunks",
        "embedding_json",
        existing_type=sa.Text(),
        nullable=False,
    )

    op.drop_index(
        "ix_internal_document_chunks_embedding_vector_ivfflat",
        table_name="internal_document_chunks",
    )

    op.drop_column("internal_document_chunks", "embedding_vector")
