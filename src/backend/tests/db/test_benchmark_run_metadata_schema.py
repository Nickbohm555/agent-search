import uuid
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models import BenchmarkRun, BenchmarkRunMode

DATABASE_URL = "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search"


def test_benchmark_run_metadata_tables_exist_with_expected_columns() -> None:
    engine = create_engine(DATABASE_URL, future=True)
    inspector = inspect(engine)

    tables = set(inspector.get_table_names())
    assert "benchmark_runs" in tables
    assert "benchmark_run_modes" in tables

    run_columns = {column["name"] for column in inspector.get_columns("benchmark_runs")}
    assert {
        "run_id",
        "status",
        "dataset_id",
        "slo_snapshot",
        "context_fingerprint",
        "corpus_hash",
        "objective_snapshot",
        "run_metadata",
        "error",
        "started_at",
        "finished_at",
        "created_at",
    }.issubset(run_columns)

    mode_columns = {column["name"] for column in inspector.get_columns("benchmark_run_modes")}
    assert {"id", "run_id", "mode", "mode_metadata", "created_at"}.issubset(mode_columns)

    unique_constraints = inspector.get_unique_constraints("benchmark_run_modes")
    assert any(
        constraint.get("name") == "uq_benchmark_run_modes_run_id_mode"
        and constraint.get("column_names") == ["run_id", "mode"]
        for constraint in unique_constraints
    )


def test_benchmark_run_modes_unique_constraint_and_cascade_delete() -> None:
    engine = create_engine(DATABASE_URL, future=True)
    run_id = f"test-run-{uuid.uuid4()}"

    with Session(engine) as session:
        run = BenchmarkRun(
            run_id=run_id,
            status="queued",
            dataset_id="internal_v1",
            slo_snapshot={"max_latency_ms_p95": 30000, "min_correctness": 0.75},
            context_fingerprint="fingerprint-abc",
            corpus_hash="corpus-hash-123",
            objective_snapshot={"primary_kpi": "correctness"},
            run_metadata={"trigger": "schema_test"},
        )
        session.add(run)
        session.flush()

        session.add(BenchmarkRunMode(run_id=run_id, mode="baseline", mode_metadata={"enabled": True}))
        session.commit()

        session.add(BenchmarkRunMode(run_id=run_id, mode="baseline", mode_metadata={"enabled": False}))
        try:
            session.commit()
            assert False, "Expected IntegrityError for duplicate (run_id, mode)"
        except IntegrityError:
            session.rollback()

        mode_count = len(session.scalars(select(BenchmarkRunMode).where(BenchmarkRunMode.run_id == run_id)).all())
        assert mode_count == 1

        db_run = session.get(BenchmarkRun, run_id)
        assert db_run is not None
        session.delete(db_run)
        session.commit()

        remaining_modes = session.scalars(select(BenchmarkRunMode).where(BenchmarkRunMode.run_id == run_id)).all()
        assert remaining_modes == []
