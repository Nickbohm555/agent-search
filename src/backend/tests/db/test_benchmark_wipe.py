from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table, create_engine, event, func, select
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from benchmarks.retention import purge_old_benchmark_runs
from common.db import wipe_all_benchmark_data


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def test_wipe_all_benchmark_data_preserves_internal_tables(caplog) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    metadata = MetaData()

    documents = Table(
        "internal_documents",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String(255), nullable=False),
    )
    chunks = Table(
        "internal_document_chunks",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("document_id", Integer, ForeignKey("internal_documents.id", ondelete="CASCADE"), nullable=False),
        Column("content", String, nullable=False),
    )
    runs = Table(
        "benchmark_runs",
        metadata,
        Column("run_id", String(128), primary_key=True),
        Column("status", String(32), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )
    run_modes = Table(
        "benchmark_run_modes",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("run_id", String(128), ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"), nullable=False),
    )
    results = Table(
        "benchmark_results",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("run_id", String(128), ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"), nullable=False),
    )
    quality_scores = Table(
        "benchmark_quality_scores",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("run_id", String(128), ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"), nullable=False),
        Column("result_id", Integer, ForeignKey("benchmark_results.id", ondelete="CASCADE"), nullable=False),
    )
    citation_scores = Table(
        "benchmark_citation_scores",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("run_id", String(128), ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"), nullable=False),
        Column("result_id", Integer, ForeignKey("benchmark_results.id", ondelete="CASCADE"), nullable=False),
    )
    verifications = Table(
        "benchmark_citation_verifications",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("citation_score_id", Integer, ForeignKey("benchmark_citation_scores.id", ondelete="CASCADE"), nullable=False),
        Column("run_id", String(128), ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"), nullable=False),
        Column("result_id", Integer, ForeignKey("benchmark_results.id", ondelete="CASCADE"), nullable=False),
    )
    retrieval_metrics = Table(
        "benchmark_retrieval_metrics",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("run_id", String(128), ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"), nullable=False),
        Column("result_id", Integer, ForeignKey("benchmark_results.id", ondelete="CASCADE"), nullable=False),
    )

    metadata.create_all(
        engine,
        tables=[
            documents,
            chunks,
            runs,
            run_modes,
            results,
            quality_scores,
            citation_scores,
            verifications,
            retrieval_metrics,
        ],
    )

    now = datetime.now(tz=UTC)
    with Session(engine) as session:
        session.execute(documents.insert(), [{"id": 1, "title": "Doc"}])
        session.execute(chunks.insert(), [{"id": 1, "document_id": 1, "content": "chunk"}])
        session.execute(runs.insert(), [{"run_id": "run-1", "status": "completed", "created_at": now}])
        session.execute(run_modes.insert(), [{"id": 1, "run_id": "run-1"}])
        session.execute(results.insert(), [{"id": 10, "run_id": "run-1"}])
        session.execute(quality_scores.insert(), [{"id": 20, "run_id": "run-1", "result_id": 10}])
        session.execute(citation_scores.insert(), [{"id": 30, "run_id": "run-1", "result_id": 10}])
        session.execute(verifications.insert(), [{"id": 40, "citation_score_id": 30, "run_id": "run-1", "result_id": 10}])
        session.execute(retrieval_metrics.insert(), [{"id": 50, "run_id": "run-1", "result_id": 10}])
        session.commit()

        with caplog.at_level(logging.INFO):
            deleted_runs = wipe_all_benchmark_data(session)
        session.commit()

        assert deleted_runs == 1
        assert session.scalar(select(func.count()).select_from(documents)) == 1
        assert session.scalar(select(func.count()).select_from(chunks)) == 1
        assert session.scalar(select(func.count()).select_from(runs)) == 0
        assert session.scalar(select(func.count()).select_from(run_modes)) == 0
        assert session.scalar(select(func.count()).select_from(results)) == 0
        assert session.scalar(select(func.count()).select_from(quality_scores)) == 0
        assert session.scalar(select(func.count()).select_from(citation_scores)) == 0
        assert session.scalar(select(func.count()).select_from(verifications)) == 0
        assert session.scalar(select(func.count()).select_from(retrieval_metrics)) == 0
        assert "Wiped benchmark data: deleted 1 benchmark run rows." in caplog.text


def test_benchmark_retention_deletes_only_old_terminal_runs(caplog) -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    metadata = MetaData()

    documents = Table(
        "internal_documents",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("title", String(255), nullable=False),
    )
    runs = Table(
        "benchmark_runs",
        metadata,
        Column("run_id", String(128), primary_key=True),
        Column("status", String(32), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )
    run_modes = Table(
        "benchmark_run_modes",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("run_id", String(128), ForeignKey("benchmark_runs.run_id", ondelete="CASCADE"), nullable=False),
    )
    metadata.create_all(engine, tables=[documents, runs, run_modes])

    now = datetime.now(tz=UTC)
    with Session(engine) as session:
        session.execute(documents.insert(), [{"id": 1, "title": "Doc"}])
        session.execute(
            runs.insert(),
            [
                {"run_id": "run-old-completed", "status": "completed", "created_at": now - timedelta(days=10)},
                {"run_id": "run-old-running", "status": "running", "created_at": now - timedelta(days=10)},
                {"run_id": "run-recent-completed", "status": "completed", "created_at": now - timedelta(hours=2)},
            ],
        )
        session.execute(
            run_modes.insert(),
            [
                {"id": 1, "run_id": "run-old-completed"},
                {"id": 2, "run_id": "run-old-running"},
                {"id": 3, "run_id": "run-recent-completed"},
            ],
        )
        session.commit()

        with caplog.at_level(logging.INFO):
            result = purge_old_benchmark_runs(
                session,
                older_than=now - timedelta(days=2),
                statuses=("completed",),
            )
        session.commit()

        assert result.candidate_runs == 1
        assert result.deleted_runs == 1
        assert session.scalar(select(func.count()).select_from(documents)) == 1
        assert session.scalar(select(func.count()).select_from(runs)) == 2
        assert session.scalar(select(func.count()).select_from(run_modes)) == 2
        remaining_runs = set(session.scalars(select(runs.c.run_id)).all())
        assert remaining_runs == {"run-old-running", "run-recent-completed"}
        assert "Benchmark retention evaluated" in caplog.text
