import uuid
import sys
from pathlib import Path

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models import BenchmarkResult, BenchmarkRun

DATABASE_URL = "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search"


def test_benchmark_results_table_exists_with_expected_columns() -> None:
    engine = create_engine(DATABASE_URL, future=True)
    inspector = inspect(engine)

    tables = set(inspector.get_table_names())
    assert "benchmark_results" in tables

    result_columns = {column["name"] for column in inspector.get_columns("benchmark_results")}
    assert {
        "id",
        "run_id",
        "mode",
        "question_id",
        "answer_payload",
        "citations",
        "latency_ms",
        "token_usage",
        "execution_error",
        "created_at",
    }.issubset(result_columns)

    unique_constraints = inspector.get_unique_constraints("benchmark_results")
    assert any(
        constraint.get("name") == "uq_benchmark_results_run_mode_question"
        and constraint.get("column_names") == ["run_id", "mode", "question_id"]
        for constraint in unique_constraints
    )


def test_benchmark_results_unique_constraint_and_cascade_delete() -> None:
    engine = create_engine(DATABASE_URL, future=True)
    run_id = f"test-results-run-{uuid.uuid4()}"

    with Session(engine) as session:
        run = BenchmarkRun(
            run_id=run_id,
            status="queued",
            dataset_id="internal_v1",
            slo_snapshot={"max_latency_ms_p95": 30000, "min_correctness": 0.75},
            context_fingerprint="fingerprint-results",
            corpus_hash="corpus-hash-results",
            objective_snapshot={"primary_kpi": "correctness"},
            run_metadata={"trigger": "schema_test"},
        )
        session.add(run)
        session.flush()

        session.add(
            BenchmarkResult(
                run_id=run_id,
                mode="baseline",
                question_id="DRB-001",
                answer_payload={"answer": "Alpha"},
                citations=[{"title": "Doc A", "source": "internal"}],
                latency_ms=1234,
                token_usage={"prompt_tokens": 100, "completion_tokens": 25, "total_tokens": 125},
                execution_error=None,
            )
        )
        session.commit()

        session.add(
            BenchmarkResult(
                run_id=run_id,
                mode="baseline",
                question_id="DRB-001",
                answer_payload={"answer": "Duplicate"},
            )
        )
        try:
            session.commit()
            assert False, "Expected IntegrityError for duplicate (run_id, mode, question_id)"
        except IntegrityError:
            session.rollback()

        result_count = len(session.scalars(select(BenchmarkResult).where(BenchmarkResult.run_id == run_id)).all())
        assert result_count == 1

        db_run = session.get(BenchmarkRun, run_id)
        assert db_run is not None
        session.delete(db_run)
        session.commit()

        remaining_results = session.scalars(select(BenchmarkResult).where(BenchmarkResult.run_id == run_id)).all()
        assert remaining_results == []
