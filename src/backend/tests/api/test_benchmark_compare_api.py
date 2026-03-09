import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db import get_db
from routers.benchmarks import router as benchmarks_router
from schemas import (
    BenchmarkMode,
    BenchmarkModeSummary,
    BenchmarkObjective,
    BenchmarkRunStatus,
    BenchmarkRunStatusResponse,
)


def _build_client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    app = FastAPI()
    app.include_router(benchmarks_router)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_get_benchmark_compare_returns_mode_deltas(monkeypatch) -> None:
    from routers import benchmarks as benchmarks_router_module

    def fake_get(*, run_id, db):  # noqa: ANN001
        del db
        assert run_id == "run-compare-1"
        return BenchmarkRunStatusResponse(
            run_id=run_id,
            status=BenchmarkRunStatus.completed,
            dataset_id="internal_v1",
            modes=[BenchmarkMode.baseline_retrieve_then_answer, BenchmarkMode.agentic_default],
            objective=BenchmarkObjective(),
            mode_summaries=[
                BenchmarkModeSummary(
                    mode=BenchmarkMode.baseline_retrieve_then_answer,
                    completed_questions=3,
                    total_questions=3,
                    correctness_rate=0.70,
                    avg_latency_ms=100.0,
                    p95_latency_ms=130.0,
                ),
                BenchmarkModeSummary(
                    mode=BenchmarkMode.agentic_default,
                    completed_questions=3,
                    total_questions=3,
                    correctness_rate=0.80,
                    avg_latency_ms=105.0,
                    p95_latency_ms=150.0,
                ),
            ],
            results=[],
            completed_questions=6,
            total_questions=6,
        )

    monkeypatch.setattr(benchmarks_router_module, "get_benchmark_run_status", fake_get)
    client = _build_client()
    response = client.get("/api/benchmarks/runs/run-compare-1/compare")
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "run-compare-1"
    assert body["baseline_mode"] == BenchmarkMode.baseline_retrieve_then_answer.value
    assert body["comparisons"][0] == {
        "mode": BenchmarkMode.baseline_retrieve_then_answer.value,
        "correctness_rate": 0.7,
        "correctness_delta": 0.0,
        "p95_latency_ms": 130.0,
        "p95_latency_delta_ms": 0.0,
    }
    assert body["comparisons"][1]["mode"] == BenchmarkMode.agentic_default.value
    assert body["comparisons"][1]["correctness_rate"] == 0.8
    assert body["comparisons"][1]["correctness_delta"] == pytest.approx(0.1)
    assert body["comparisons"][1]["p95_latency_ms"] == 150.0
    assert body["comparisons"][1]["p95_latency_delta_ms"] == 20.0


def test_get_benchmark_compare_returns_404_when_run_missing(monkeypatch) -> None:
    from routers import benchmarks as benchmarks_router_module

    monkeypatch.setattr(benchmarks_router_module, "get_benchmark_run_status", lambda *, run_id, db: None)
    client = _build_client()
    response = client.get("/api/benchmarks/runs/nope/compare")
    assert response.status_code == 404
    assert response.json() == {"detail": "Benchmark run not found."}


def test_get_benchmark_compare_returns_400_when_baseline_missing(monkeypatch) -> None:
    from routers import benchmarks as benchmarks_router_module

    def fake_get(*, run_id, db):  # noqa: ANN001
        del db
        return BenchmarkRunStatusResponse(
            run_id=run_id,
            status=BenchmarkRunStatus.completed,
            dataset_id="internal_v1",
            modes=[BenchmarkMode.agentic_default],
            objective=BenchmarkObjective(),
            mode_summaries=[
                BenchmarkModeSummary(
                    mode=BenchmarkMode.agentic_default,
                    completed_questions=1,
                    total_questions=1,
                    correctness_rate=1.0,
                    avg_latency_ms=110.0,
                    p95_latency_ms=110.0,
                )
            ],
            results=[],
            completed_questions=1,
            total_questions=1,
        )

    monkeypatch.setattr(benchmarks_router_module, "get_benchmark_run_status", fake_get)
    client = _build_client()
    response = client.get("/api/benchmarks/runs/run-compare-2/compare")
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Baseline mode summary missing for run: baseline_retrieve_then_answer",
    }
