"""Add runtime execution durability tables

Revision ID: 008_runtime_execution_durability
Revises: 007_benchmark_retrieval_metrics
Create Date: 2026-03-12

"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "008_runtime_execution_durability"
down_revision: Union[str, None] = "007_benchmark_retrieval_metrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    logger.info("Applying migration 008_runtime_execution_durability: creating runtime durability tables")
    op.create_table(
        "runtime_execution_runs",
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("run_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_runtime_execution_runs_idempotency_key"),
    )
    op.create_index("ix_runtime_execution_runs_thread_id", "runtime_execution_runs", ["thread_id"], unique=False)
    op.create_index("ix_runtime_execution_runs_status", "runtime_execution_runs", ["status"], unique=False)

    op.create_table(
        "runtime_checkpoint_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("checkpoint_namespace", sa.String(length=255), nullable=False, server_default=sa.text("''")),
        sa.Column("checkpoint_id", sa.String(length=255), nullable=False),
        sa.Column("parent_checkpoint_id", sa.String(length=255), nullable=True),
        sa.Column("checkpoint_metadata", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_latest", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["run_id"], ["runtime_execution_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "checkpoint_namespace", name="uq_runtime_checkpoint_links_run_namespace"),
        sa.UniqueConstraint(
            "thread_id",
            "checkpoint_namespace",
            "checkpoint_id",
            name="uq_runtime_checkpoint_links_thread_namespace_checkpoint",
        ),
    )
    op.create_index("ix_runtime_checkpoint_links_run_id", "runtime_checkpoint_links", ["run_id"], unique=False)
    op.create_index("ix_runtime_checkpoint_links_thread_id", "runtime_checkpoint_links", ["thread_id"], unique=False)
    op.create_index(
        "ix_runtime_checkpoint_links_checkpoint_lookup",
        "runtime_checkpoint_links",
        ["thread_id", "checkpoint_namespace", "is_latest"],
        unique=False,
    )

    op.create_table(
        "runtime_idempotency_effects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.String(length=128), nullable=False),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column("node_name", sa.String(length=128), nullable=False),
        sa.Column("effect_key", sa.String(length=255), nullable=False),
        sa.Column("effect_status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("request_payload", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("response_payload", sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("first_recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["run_id"], ["runtime_execution_runs.run_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "thread_id",
            "node_name",
            "effect_key",
            name="uq_runtime_idempotency_effects_thread_node_effect",
        ),
    )
    op.create_index("ix_runtime_idempotency_effects_run_id", "runtime_idempotency_effects", ["run_id"], unique=False)
    op.create_index("ix_runtime_idempotency_effects_thread_id", "runtime_idempotency_effects", ["thread_id"], unique=False)
    op.create_index(
        "ix_runtime_idempotency_effects_status_lookup",
        "runtime_idempotency_effects",
        ["thread_id", "node_name", "effect_status"],
        unique=False,
    )
    logger.info("Migration 008_runtime_execution_durability complete")


def downgrade() -> None:
    logger.info("Reverting migration 008_runtime_execution_durability")
    op.drop_index("ix_runtime_idempotency_effects_status_lookup", table_name="runtime_idempotency_effects")
    op.drop_index("ix_runtime_idempotency_effects_thread_id", table_name="runtime_idempotency_effects")
    op.drop_index("ix_runtime_idempotency_effects_run_id", table_name="runtime_idempotency_effects")
    op.drop_table("runtime_idempotency_effects")

    op.drop_index("ix_runtime_checkpoint_links_checkpoint_lookup", table_name="runtime_checkpoint_links")
    op.drop_index("ix_runtime_checkpoint_links_thread_id", table_name="runtime_checkpoint_links")
    op.drop_index("ix_runtime_checkpoint_links_run_id", table_name="runtime_checkpoint_links")
    op.drop_table("runtime_checkpoint_links")

    op.drop_index("ix_runtime_execution_runs_status", table_name="runtime_execution_runs")
    op.drop_index("ix_runtime_execution_runs_thread_id", table_name="runtime_execution_runs")
    op.drop_table("runtime_execution_runs")
    logger.info("Migration 008_runtime_execution_durability reverted")
