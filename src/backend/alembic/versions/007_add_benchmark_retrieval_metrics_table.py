"""Add benchmark retrieval metrics table

Revision ID: 007_benchmark_retrieval_metrics
Revises: 006_benchmark_timing_fields
Create Date: 2026-03-09

"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "007_benchmark_retrieval_metrics"
down_revision: Union[str, None] = "006_benchmark_timing_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    logger.info("Applying migration 007_benchmark_retrieval_metrics: creating benchmark_retrieval_metrics table")
    op.create_table(
        "benchmark_retrieval_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=64), nullable=False),
        sa.Column("question_id", sa.String(length=128), nullable=False),
        sa.Column("recall_at_k", sa.Float(), nullable=True),
        sa.Column("mrr", sa.Float(), nullable=True),
        sa.Column("ndcg", sa.Float(), nullable=True),
        sa.Column("k", sa.Integer(), nullable=False, server_default=sa.text("10")),
        sa.Column("retrieved_document_ids", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("relevant_document_ids", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("label_source", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["result_id"], ["benchmark_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["benchmark_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("result_id", name="uq_benchmark_retrieval_metrics_result_id"),
        sa.UniqueConstraint("run_id", "mode", "question_id", name="uq_benchmark_retrieval_metrics_run_mode_question"),
    )
    op.create_index("ix_benchmark_retrieval_metrics_run_id", "benchmark_retrieval_metrics", ["run_id"], unique=False)
    op.create_index("ix_benchmark_retrieval_metrics_result_id", "benchmark_retrieval_metrics", ["result_id"], unique=False)
    op.create_index(
        "ix_benchmark_retrieval_metrics_mode_question_id",
        "benchmark_retrieval_metrics",
        ["mode", "question_id"],
        unique=False,
    )
    logger.info("Migration 007_benchmark_retrieval_metrics complete")


def downgrade() -> None:
    logger.info("Reverting migration 007_benchmark_retrieval_metrics")
    op.drop_index("ix_benchmark_retrieval_metrics_mode_question_id", table_name="benchmark_retrieval_metrics")
    op.drop_index("ix_benchmark_retrieval_metrics_result_id", table_name="benchmark_retrieval_metrics")
    op.drop_index("ix_benchmark_retrieval_metrics_run_id", table_name="benchmark_retrieval_metrics")
    op.drop_table("benchmark_retrieval_metrics")
    logger.info("Migration 007_benchmark_retrieval_metrics reverted")
