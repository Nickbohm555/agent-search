from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Sequence

from sqlalchemy import Column, DateTime, MetaData, String, Table, delete, select
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db import SessionLocal

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_STATUSES = ("completed", "failed", "cancelled")

_metadata = MetaData()
_benchmark_runs = Table(
    "benchmark_runs",
    _metadata,
    Column("run_id", String(128), primary_key=True),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


@dataclass(frozen=True)
class BenchmarkRetentionResult:
    candidate_runs: int
    deleted_runs: int
    dry_run: bool
    cutoff_utc: datetime
    statuses: tuple[str, ...]
    limit: int | None


def purge_old_benchmark_runs(
    session: Session,
    *,
    older_than: datetime,
    statuses: Sequence[str] = DEFAULT_RETENTION_STATUSES,
    limit: int | None = None,
    dry_run: bool = False,
) -> BenchmarkRetentionResult:
    """Delete old benchmark runs by status and age. Returns a deterministic summary."""
    if older_than.tzinfo is None:
        older_than = older_than.replace(tzinfo=UTC)
    else:
        older_than = older_than.astimezone(UTC)

    normalized_statuses = tuple(dict.fromkeys(status.strip() for status in statuses if status.strip()))
    if not normalized_statuses:
        raise ValueError("At least one status is required for benchmark retention.")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive when provided.")

    run_query = (
        select(_benchmark_runs.c.run_id)
        .where(_benchmark_runs.c.created_at < older_than)
        .where(_benchmark_runs.c.status.in_(normalized_statuses))
        .order_by(_benchmark_runs.c.created_at.asc())
    )
    if limit is not None:
        run_query = run_query.limit(limit)

    run_ids = list(session.scalars(run_query).all())
    candidate_count = len(run_ids)
    deleted_count = 0

    if run_ids and not dry_run:
        delete_result = session.execute(delete(_benchmark_runs).where(_benchmark_runs.c.run_id.in_(run_ids)))
        session.flush()
        deleted_count = delete_result.rowcount or 0

    logger.info(
        "Benchmark retention evaluated cutoff_utc=%s statuses=%s candidate_runs=%s deleted_runs=%s dry_run=%s limit=%s",
        older_than.isoformat(),
        normalized_statuses,
        candidate_count,
        deleted_count,
        dry_run,
        limit,
    )
    return BenchmarkRetentionResult(
        candidate_runs=candidate_count,
        deleted_runs=deleted_count,
        dry_run=dry_run,
        cutoff_utc=older_than,
        statuses=normalized_statuses,
        limit=limit,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Delete old benchmark runs with status/date filters.")
    parser.add_argument(
        "--older-than-days",
        type=int,
        default=30,
        help="Delete runs older than this many days (default: 30).",
    )
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        help="Run status to include; repeat for multiple values (default: completed,failed,cancelled).",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of runs to delete.")
    parser.add_argument("--dry-run", action="store_true", help="Show matches without deleting rows.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    cutoff = datetime.now(tz=UTC) - timedelta(days=args.older_than_days)
    statuses = tuple(args.statuses) if args.statuses else DEFAULT_RETENTION_STATUSES

    with SessionLocal() as session:
        result = purge_old_benchmark_runs(
            session,
            older_than=cutoff,
            statuses=statuses,
            limit=args.limit,
            dry_run=args.dry_run,
        )
        if not args.dry_run:
            session.commit()
            logger.info("Benchmark retention committed deleted_runs=%s", result.deleted_runs)
        else:
            logger.info("Benchmark retention dry-run complete candidate_runs=%s", result.candidate_runs)

    print(
        "benchmark_retention",
        f"candidate_runs={result.candidate_runs}",
        f"deleted_runs={result.deleted_runs}",
        f"dry_run={result.dry_run}",
        f"cutoff_utc={result.cutoff_utc.isoformat()}",
        f"statuses={','.join(result.statuses)}",
        f"limit={result.limit}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
