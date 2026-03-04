"""migrate chunk embeddings to pgvector

Revision ID: 0003_pgvector_chunk_embeddings
Revises: 0002_internal_data_tables
Create Date: 2026-03-04 16:05:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision: str = "0003_pgvector_chunk_embeddings"
down_revision: Union[str, None] = "0002_internal_data_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "internal_document_chunks",
        sa.Column("embedding", Vector(16), nullable=True),
    )
    op.execute(
        """
        UPDATE internal_document_chunks
        SET embedding = embedding_json::vector
        WHERE embedding IS NULL
        """
    )
    op.alter_column("internal_document_chunks", "embedding", nullable=False)
    op.drop_column("internal_document_chunks", "embedding_json")


def downgrade() -> None:
    op.add_column(
        "internal_document_chunks",
        sa.Column("embedding_json", sa.Text(), nullable=True),
    )
    op.execute(
        """
        UPDATE internal_document_chunks
        SET embedding_json = embedding::text
        WHERE embedding_json IS NULL
        """
    )
    op.alter_column("internal_document_chunks", "embedding_json", nullable=False)
    op.drop_column("internal_document_chunks", "embedding")
