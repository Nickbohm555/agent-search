"""Add benchmark run metadata tables

Revision ID: 002_benchmark_run_metadata
Revises: 001_internal
Create Date: 2026-03-09

"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "002_benchmark_run_metadata"
down_revision: Union[str, None] = "001_internal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    logger.info("Applying migration 002_benchmark_run_metadata: creating benchmark metadata tables")

    op.create_table(
        "benchmark_runs",
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("dataset_id", sa.String(length=255), nullable=False),
        sa.Column("slo_snapshot", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("context_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("corpus_hash", sa.String(length=128), nullable=False),
        sa.Column("objective_snapshot", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "run_metadata",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index("ix_benchmark_runs_status", "benchmark_runs", ["status"], unique=False)
    op.create_index(
        "ix_benchmark_runs_context_fingerprint",
        "benchmark_runs",
        ["context_fingerprint"],
        unique=False,
    )

    op.create_table(
        "benchmark_run_modes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("mode", sa.String(length=64), nullable=False),
        sa.Column(
            "mode_metadata",
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["benchmark_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "mode", name="uq_benchmark_run_modes_run_id_mode"),
    )
    op.create_index("ix_benchmark_run_modes_run_id", "benchmark_run_modes", ["run_id"], unique=False)

    logger.info("Migration 002_benchmark_run_metadata complete")


def downgrade() -> None:
    logger.info("Reverting migration 002_benchmark_run_metadata")
    op.drop_index("ix_benchmark_run_modes_run_id", table_name="benchmark_run_modes")
    op.drop_table("benchmark_run_modes")
    op.drop_index("ix_benchmark_runs_context_fingerprint", table_name="benchmark_runs")
    op.drop_index("ix_benchmark_runs_status", table_name="benchmark_runs")
    op.drop_table("benchmark_runs")
    logger.info("Migration 002_benchmark_run_metadata reverted")
