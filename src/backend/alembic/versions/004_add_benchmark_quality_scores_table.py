"""Add benchmark_quality_scores table

Revision ID: 004_benchmark_quality_scores
Revises: 003_benchmark_results
Create Date: 2026-03-09

"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "004_benchmark_quality_scores"
down_revision: Union[str, None] = "003_benchmark_results"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    logger.info("Applying migration 004_benchmark_quality_scores: creating benchmark_quality_scores table")

    op.create_table(
        "benchmark_quality_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=64), nullable=False),
        sa.Column("question_id", sa.String(length=128), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("rubric_version", sa.String(length=32), nullable=False),
        sa.Column("judge_model", sa.String(length=128), nullable=False),
        sa.Column("subscores_json", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["result_id"], ["benchmark_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["benchmark_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("result_id", name="uq_benchmark_quality_scores_result_id"),
        sa.UniqueConstraint("run_id", "mode", "question_id", name="uq_benchmark_quality_scores_run_mode_question"),
    )
    op.create_index("ix_benchmark_quality_scores_run_id", "benchmark_quality_scores", ["run_id"], unique=False)
    op.create_index("ix_benchmark_quality_scores_result_id", "benchmark_quality_scores", ["result_id"], unique=False)
    op.create_index(
        "ix_benchmark_quality_scores_mode_question_id",
        "benchmark_quality_scores",
        ["mode", "question_id"],
        unique=False,
    )

    logger.info("Migration 004_benchmark_quality_scores complete")


def downgrade() -> None:
    logger.info("Reverting migration 004_benchmark_quality_scores")
    op.drop_index("ix_benchmark_quality_scores_mode_question_id", table_name="benchmark_quality_scores")
    op.drop_index("ix_benchmark_quality_scores_result_id", table_name="benchmark_quality_scores")
    op.drop_index("ix_benchmark_quality_scores_run_id", table_name="benchmark_quality_scores")
    op.drop_table("benchmark_quality_scores")
    logger.info("Migration 004_benchmark_quality_scores reverted")
