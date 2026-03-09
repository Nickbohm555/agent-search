import logging

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table, delete, func, select, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_metadata = MetaData()
_benchmark_runs = Table(
    "benchmark_runs",
    _metadata,
    Column("run_id", String(128), primary_key=True),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)
_benchmark_run_modes = Table(
    "benchmark_run_modes",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("run_id", String(128), ForeignKey("benchmark_runs.run_id"), nullable=False),
)
_benchmark_results = Table(
    "benchmark_results",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("run_id", String(128), ForeignKey("benchmark_runs.run_id"), nullable=False),
)
_benchmark_quality_scores = Table(
    "benchmark_quality_scores",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("run_id", String(128), ForeignKey("benchmark_runs.run_id"), nullable=False),
    Column("result_id", Integer, ForeignKey("benchmark_results.id"), nullable=False),
)
_benchmark_citation_scores = Table(
    "benchmark_citation_scores",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("run_id", String(128), ForeignKey("benchmark_runs.run_id"), nullable=False),
    Column("result_id", Integer, ForeignKey("benchmark_results.id"), nullable=False),
)
_benchmark_citation_verifications = Table(
    "benchmark_citation_verifications",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("citation_score_id", Integer, ForeignKey("benchmark_citation_scores.id"), nullable=False),
    Column("run_id", String(128), ForeignKey("benchmark_runs.run_id"), nullable=False),
    Column("result_id", Integer, ForeignKey("benchmark_results.id"), nullable=False),
)
_benchmark_retrieval_metrics = Table(
    "benchmark_retrieval_metrics",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("run_id", String(128), ForeignKey("benchmark_runs.run_id"), nullable=False),
    Column("result_id", Integer, ForeignKey("benchmark_results.id"), nullable=False),
)


def wipe_all_benchmark_data(session: Session) -> int:
    """Delete only benchmark rows and keep non-benchmark tables untouched."""
    deleted_runs = session.scalar(select(func.count()).select_from(_benchmark_runs)) or 0
    dialect = session.bind.dialect.name if session.bind is not None else ""

    if dialect == "postgresql":
        session.execute(
            text(
                "TRUNCATE "
                "benchmark_citation_verifications, "
                "benchmark_retrieval_metrics, "
                "benchmark_citation_scores, "
                "benchmark_quality_scores, "
                "benchmark_results, "
                "benchmark_run_modes, "
                "benchmark_runs "
                "RESTART IDENTITY CASCADE",
            ),
        )
        session.flush()
        logger.info("Wiped benchmark data via TRUNCATE deleted_runs=%s", deleted_runs)
        return int(deleted_runs)

    # SQLite path used by tests: clear children first when FK enforcement is enabled.
    session.execute(delete(_benchmark_citation_verifications))
    session.execute(delete(_benchmark_retrieval_metrics))
    session.execute(delete(_benchmark_citation_scores))
    session.execute(delete(_benchmark_quality_scores))
    session.execute(delete(_benchmark_results))
    session.execute(delete(_benchmark_run_modes))
    run_result = session.execute(delete(_benchmark_runs))
    session.flush()

    run_rows = run_result.rowcount if run_result.rowcount is not None else 0
    logger.info("Wiped benchmark data: deleted %s benchmark run rows.", run_rows)
    return run_rows
