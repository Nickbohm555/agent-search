"""Add benchmark citation evaluation tables

Revision ID: 005_benchmark_citation_tables
Revises: 004_benchmark_quality_scores
Create Date: 2026-03-09

"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "005_benchmark_citation_tables"
down_revision: Union[str, None] = "004_benchmark_quality_scores"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    logger.info("Applying migration 005_benchmark_citation_tables")

    op.create_table(
        "benchmark_citation_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=64), nullable=False),
        sa.Column("question_id", sa.String(length=128), nullable=False),
        sa.Column("citation_presence_rate", sa.Float(), nullable=False),
        sa.Column("basic_support_rate", sa.Float(), nullable=False),
        sa.Column("evaluator_version", sa.String(length=32), nullable=False),
        sa.Column("total_citation_count", sa.Integer(), nullable=False),
        sa.Column("found_citation_count", sa.Integer(), nullable=False),
        sa.Column("supported_citation_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["result_id"], ["benchmark_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["benchmark_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("result_id", name="uq_benchmark_citation_scores_result_id"),
        sa.UniqueConstraint("run_id", "mode", "question_id", name="uq_benchmark_citation_scores_run_mode_question"),
    )
    op.create_index("ix_benchmark_citation_scores_run_id", "benchmark_citation_scores", ["run_id"], unique=False)
    op.create_index("ix_benchmark_citation_scores_result_id", "benchmark_citation_scores", ["result_id"], unique=False)
    op.create_index(
        "ix_benchmark_citation_scores_mode_question_id",
        "benchmark_citation_scores",
        ["mode", "question_id"],
        unique=False,
    )

    op.create_table(
        "benchmark_citation_verifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("citation_score_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=64), nullable=False),
        sa.Column("question_id", sa.String(length=128), nullable=False),
        sa.Column("citation_marker", sa.String(length=32), nullable=False),
        sa.Column("citation_index", sa.Integer(), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("citation_found", sa.Boolean(), nullable=False),
        sa.Column("is_supported", sa.Boolean(), nullable=False),
        sa.Column("support_label", sa.String(length=32), nullable=False),
        sa.Column("support_evidence", sa.Text(), nullable=True),
        sa.Column("verification_payload", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "verification_type",
            sa.String(length=64),
            server_default=sa.text("'citation_support_v1'"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["citation_score_id"], ["benchmark_citation_scores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["result_id"], ["benchmark_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["benchmark_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_benchmark_citation_verifications_citation_score_id",
        "benchmark_citation_verifications",
        ["citation_score_id"],
        unique=False,
    )
    op.create_index(
        "ix_benchmark_citation_verifications_run_id",
        "benchmark_citation_verifications",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_benchmark_citation_verifications_result_id",
        "benchmark_citation_verifications",
        ["result_id"],
        unique=False,
    )
    op.create_index(
        "ix_benchmark_citation_verifications_mode_question_id",
        "benchmark_citation_verifications",
        ["mode", "question_id"],
        unique=False,
    )
    logger.info("Migration 005_benchmark_citation_tables complete")


def downgrade() -> None:
    logger.info("Reverting migration 005_benchmark_citation_tables")
    op.drop_index(
        "ix_benchmark_citation_verifications_mode_question_id",
        table_name="benchmark_citation_verifications",
    )
    op.drop_index("ix_benchmark_citation_verifications_result_id", table_name="benchmark_citation_verifications")
    op.drop_index("ix_benchmark_citation_verifications_run_id", table_name="benchmark_citation_verifications")
    op.drop_index(
        "ix_benchmark_citation_verifications_citation_score_id",
        table_name="benchmark_citation_verifications",
    )
    op.drop_table("benchmark_citation_verifications")

    op.drop_index("ix_benchmark_citation_scores_mode_question_id", table_name="benchmark_citation_scores")
    op.drop_index("ix_benchmark_citation_scores_result_id", table_name="benchmark_citation_scores")
    op.drop_index("ix_benchmark_citation_scores_run_id", table_name="benchmark_citation_scores")
    op.drop_table("benchmark_citation_scores")
    logger.info("Migration 005_benchmark_citation_tables reverted")
