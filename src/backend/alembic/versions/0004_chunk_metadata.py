"""add chunk metadata column

Revision ID: 0004_chunk_metadata
Revises: 0003_pgvector_chunk_embeddings
Create Date: 2026-03-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004_chunk_metadata"
down_revision: Union[str, None] = "0003_pgvector_chunk_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "internal_document_chunks",
        sa.Column("chunk_metadata", JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("internal_document_chunks", "chunk_metadata")
