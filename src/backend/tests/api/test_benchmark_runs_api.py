import sys
from pathlib import Path

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
    BenchmarkResultQualityScore,
    BenchmarkResultStatusItem,
    BenchmarkRunListItem,
    BenchmarkRunListResponse,
    BenchmarkRunStatus,
    BenchmarkRunStatusResponse,
    BenchmarkTargets,
)


def _build_client():
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


def test_create_benchmark_run_returns_create_shape(monkeypatch) -> None:
    from routers import benchmarks as benchmarks_router_module
    from schemas import BenchmarkRunCreateResponse

    captured: dict[str, object] = {}

    def fake_start(payload):
        captured["dataset_id"] = payload.dataset_id
        captured["modes"] = payload.modes
        return BenchmarkRunCreateResponse(run_id="benchmark-run-123", status=BenchmarkRunStatus.queued)

    monkeypatch.setattr(benchmarks_router_module, "start_benchmark_run_job", fake_start)
    client = _build_client()
    response = client.post(
        "/api/benchmarks/runs",
        json={"dataset_id": "internal_v1", "modes": [BenchmarkMode.agentic_default.value], "metadata": {"trigger": "test"}},
    )
    assert response.status_code == 200
    assert response.json() == {"run_id": "benchmark-run-123", "status": "queued"}
    assert captured == {
        "dataset_id": "internal_v1",
        "modes": [BenchmarkMode.agentic_default],
    }


def test_list_benchmark_runs_returns_list_shape(monkeypatch) -> None:
    from routers import benchmarks as benchmarks_router_module

    def fake_list(*, db):  # noqa: ANN001
        del db
        return BenchmarkRunListResponse(
            runs=[
                BenchmarkRunListItem(
                    run_id="run-1",
                    status=BenchmarkRunStatus.running,
                    dataset_id="internal_v1",
                    modes=[BenchmarkMode.agentic_default],
                    created_at=1.0,
                    started_at=2.0,
                    finished_at=None,
                )
            ]
        )

    monkeypatch.setattr(benchmarks_router_module, "list_benchmark_runs", fake_list)
    client = _build_client()
    response = client.get("/api/benchmarks/runs")
    assert response.status_code == 200
    assert response.json() == {
        "runs": [
            {
                "run_id": "run-1",
                "status": "running",
                "dataset_id": "internal_v1",
                "modes": [BenchmarkMode.agentic_default.value],
                "created_at": 1.0,
                "started_at": 2.0,
                "finished_at": None,
            }
        ]
    }


def test_get_benchmark_run_returns_status_shape(monkeypatch) -> None:
    from routers import benchmarks as benchmarks_router_module

    def fake_get(*, run_id, db):  # noqa: ANN001
        del db
        assert run_id == "run-2"
        return BenchmarkRunStatusResponse(
            run_id=run_id,
            status=BenchmarkRunStatus.completed,
            dataset_id="internal_v1",
            modes=[BenchmarkMode.agentic_default],
            objective=BenchmarkObjective(),
            targets=BenchmarkTargets(),
            mode_summaries=[
                BenchmarkModeSummary(
                    mode=BenchmarkMode.agentic_default,
                    completed_questions=3,
                    total_questions=3,
                    correctness_rate=1.0,
                    avg_latency_ms=120.0,
                    p95_latency_ms=150.0,
                )
            ],
            results=[
                BenchmarkResultStatusItem(
                    mode=BenchmarkMode.agentic_default.value,
                    question_id="DRB-001",
                    latency_ms=120,
                    execution_error=None,
                    quality=BenchmarkResultQualityScore(
                        score=0.92,
                        passed=True,
                        rubric_version="v1",
                        judge_model="gpt-test-judge",
                        subscores={"coverage": 0.92},
                    ),
                )
            ],
            completed_questions=3,
            total_questions=3,
            created_at=1.0,
            started_at=2.0,
            finished_at=3.0,
            error=None,
        )

    monkeypatch.setattr(benchmarks_router_module, "get_benchmark_run_status", fake_get)
    client = _build_client()
    response = client.get("/api/benchmarks/runs/run-2")
    assert response.status_code == 200
    assert response.json() == {
        "run_id": "run-2",
        "status": "completed",
        "dataset_id": "internal_v1",
        "modes": [BenchmarkMode.agentic_default.value],
        "objective": {
            "primary_kpi": "correctness",
            "secondary_kpi": "latency",
            "execution_mode": "manual_only",
            "targets": {
                "min_correctness": 0.75,
                "max_latency_ms_p95": 30000,
                "max_cost_usd": 5.0,
            },
        },
        "targets": {
            "min_correctness": 0.75,
            "max_latency_ms_p95": 30000,
            "max_cost_usd": 5.0,
        },
        "mode_summaries": [
            {
                "mode": BenchmarkMode.agentic_default.value,
                "completed_questions": 3,
                "total_questions": 3,
                "correctness_rate": 1.0,
                "avg_latency_ms": 120.0,
                "p95_latency_ms": 150.0,
            }
        ],
        "results": [
            {
                "mode": BenchmarkMode.agentic_default.value,
                "question_id": "DRB-001",
                "latency_ms": 120,
                "execution_error": None,
                "quality": {
                    "score": 0.92,
                    "passed": True,
                    "rubric_version": "v1",
                    "judge_model": "gpt-test-judge",
                    "subscores": {"coverage": 0.92},
                    "error": None,
                },
                "retrieval": None,
            }
        ],
        "completed_questions": 3,
        "total_questions": 3,
        "created_at": 1.0,
        "started_at": 2.0,
        "finished_at": 3.0,
        "error": None,
    }


def test_get_benchmark_run_returns_404_when_missing(monkeypatch) -> None:
    from routers import benchmarks as benchmarks_router_module

    monkeypatch.setattr(benchmarks_router_module, "get_benchmark_run_status", lambda *, run_id, db: None)
    client = _build_client()
    response = client.get("/api/benchmarks/runs/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Benchmark run not found."}


def test_cancel_benchmark_run_returns_success_shape(monkeypatch) -> None:
    from routers import benchmarks as benchmarks_router_module

    def fake_cancel(*, run_id, db):  # noqa: ANN001
        del db
        return run_id == "run-3"

    monkeypatch.setattr(benchmarks_router_module, "cancel_benchmark_run", fake_cancel)
    client = _build_client()
    response = client.post("/api/benchmarks/runs/run-3/cancel")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Cancellation requested."}


def test_cancel_benchmark_run_returns_404_when_missing(monkeypatch) -> None:
    from routers import benchmarks as benchmarks_router_module

    monkeypatch.setattr(benchmarks_router_module, "cancel_benchmark_run", lambda *, run_id, db: False)
    client = _build_client()
    response = client.post("/api/benchmarks/runs/nope/cancel")
    assert response.status_code == 404
    assert response.json() == {"detail": "Benchmark run not found or already finished."}


def test_wipe_benchmark_data_returns_success_shape(monkeypatch) -> None:
    from routers import benchmarks as benchmarks_router_module

    monkeypatch.setattr(benchmarks_router_module, "wipe_all_benchmark_data", lambda db: 7)
    client = _build_client()
    response = client.post("/api/benchmarks/wipe")
    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "message": "All benchmark run data removed.",
        "deleted_runs": 7,
    }


def test_wipe_benchmark_data_returns_500_on_error(monkeypatch) -> None:
    from routers import benchmarks as benchmarks_router_module

    def _raise(_db):  # noqa: ANN001
        raise RuntimeError("boom")

    monkeypatch.setattr(benchmarks_router_module, "wipe_all_benchmark_data", _raise)
    client = _build_client()
    response = client.post("/api/benchmarks/wipe")
    assert response.status_code == 500
    assert response.json() == {"detail": "Failed to wipe benchmark data."}
