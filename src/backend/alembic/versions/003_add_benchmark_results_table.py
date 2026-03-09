"""Add benchmark_results table

Revision ID: 003_benchmark_results
Revises: 002_benchmark_run_metadata
Create Date: 2026-03-09

"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "003_benchmark_results"
down_revision: Union[str, None] = "002_benchmark_run_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    logger.info("Applying migration 003_benchmark_results: creating benchmark_results table")

    op.create_table(
        "benchmark_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("mode", sa.String(length=64), nullable=False),
        sa.Column("question_id", sa.String(length=128), nullable=False),
        sa.Column("answer_payload", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "citations",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("token_usage", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("execution_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["benchmark_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "mode", "question_id", name="uq_benchmark_results_run_mode_question"),
    )
    op.create_index("ix_benchmark_results_run_id", "benchmark_results", ["run_id"], unique=False)
    op.create_index("ix_benchmark_results_mode", "benchmark_results", ["mode"], unique=False)

    logger.info("Migration 003_benchmark_results complete")


def downgrade() -> None:
    logger.info("Reverting migration 003_benchmark_results")
    op.drop_index("ix_benchmark_results_mode", table_name="benchmark_results")
    op.drop_index("ix_benchmark_results_run_id", table_name="benchmark_results")
    op.drop_table("benchmark_results")
    logger.info("Migration 003_benchmark_results reverted")
