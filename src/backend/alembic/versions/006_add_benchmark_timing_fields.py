"""Add benchmark result timing fields

Revision ID: 006_benchmark_timing_fields
Revises: 005_benchmark_citation_tables
Create Date: 2026-03-09

"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "006_benchmark_timing_fields"
down_revision: Union[str, None] = "005_benchmark_citation_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    logger.info("Applying migration 006_benchmark_timing_fields")
    op.add_column("benchmark_results", sa.Column("e2e_latency_ms", sa.Integer(), nullable=True))
    op.add_column("benchmark_results", sa.Column("stage_timings", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("benchmark_results", sa.Column("timing_outcome", sa.String(length=32), nullable=True))
    logger.info("Migration 006_benchmark_timing_fields complete")


def downgrade() -> None:
    logger.info("Reverting migration 006_benchmark_timing_fields")
    op.drop_column("benchmark_results", "timing_outcome")
    op.drop_column("benchmark_results", "stage_timings")
    op.drop_column("benchmark_results", "e2e_latency_ms")
    logger.info("Migration 006_benchmark_timing_fields reverted")
