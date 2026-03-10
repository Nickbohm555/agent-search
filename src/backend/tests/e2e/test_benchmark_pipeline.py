from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from common.db import wipe_all_benchmark_data
from db import SessionLocal
from main import app
from models import BenchmarkQualityScore, BenchmarkResult, BenchmarkRun, BenchmarkRunMode
from schemas import BenchmarkMode, CitationSourceRow, RuntimeAgentRunResponse
from routers import internal_data as internal_data_router
from schemas import InternalDataLoadResponse
from services import benchmark_execution_adapter, benchmark_jobs, benchmark_quality_service


@pytest.fixture(autouse=True)
def _enable_benchmarks(monkeypatch) -> None:
    monkeypatch.setenv("BENCHMARKS_ENABLED", "true")


class _InlineExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)

        class _CompletedFuture:
            def result(self):
                return None

        return _CompletedFuture()


def _clear_state() -> None:
    with SessionLocal() as session:
        wipe_all_benchmark_data(session)
        session.commit()
    with benchmark_jobs._JOB_LOCK:
        benchmark_jobs._JOBS.clear()


def _poll_status(client: TestClient, run_id: str, timeout_s: float = 5.0) -> dict[str, object]:
    deadline = time.time() + timeout_s
    last_status: dict[str, object] | None = None
    while time.time() < deadline:
        response = client.get(f"/api/benchmarks/runs/{run_id}")
        if response.status_code == 200:
            payload = response.json()
            last_status = payload
            if payload.get("status") in {"completed", "failed", "cancelled", "cancelling"}:
                return payload
        time.sleep(0.05)
    if last_status is None:
        raise AssertionError(f"Run status never became available for run_id={run_id}")
    return last_status


def test_benchmark_pipeline_happy_path_runs_end_to_end_with_compare_and_dashboard_views(monkeypatch) -> None:
    _clear_state()
    monkeypatch.setattr(benchmark_jobs, "_EXECUTOR", _InlineExecutor())
    monkeypatch.setattr(benchmark_jobs, "_build_runtime_dependencies", lambda: (object(), "model-test"))
    monkeypatch.setattr(
        internal_data_router,
        "load_internal_data",
        lambda payload, db: InternalDataLoadResponse(  # noqa: ARG005
            status="success",
            source_type="wiki",
            documents_loaded=1,
            chunks_created=2,
        ),
    )

    def fake_run_sync(self, query: str, *, vector_store, model, config=None):  # noqa: ANN001
        del self, vector_store, model, config
        return RuntimeAgentRunResponse(
            output=f"answer::{query}",
            final_citations=[
                CitationSourceRow(
                    citation_index=1,
                    rank=1,
                    title="Internal doc",
                    source="wiki://stub",
                    document_id="doc-1",
                )
            ],
        )

    def fake_quality_persist(  # noqa: PLR0913
        self,
        *,
        result_id: int,
        question_text: str,
        expected_answer_points: list[str],
        required_sources: list[str],
        run_metadata=None,  # noqa: ANN001
        rubric_version: str = "v1",
        pass_threshold=None,  # noqa: ANN001
    ):
        del expected_answer_points, required_sources, run_metadata, pass_threshold
        with self._session_factory() as session:
            result = session.get(BenchmarkResult, result_id)
            assert result is not None
            row = session.scalar(
                select(BenchmarkQualityScore).where(
                    BenchmarkQualityScore.run_id == result.run_id,
                    BenchmarkQualityScore.mode == result.mode,
                    BenchmarkQualityScore.question_id == result.question_id,
                )
            )
            if row is None:
                row = BenchmarkQualityScore(
                    run_id=result.run_id,
                    result_id=result.id,
                    mode=result.mode,
                    question_id=result.question_id,
                )
                session.add(row)
            row.result_id = result.id
            row.score = 0.95 if "first" in question_text.lower() else 0.85
            row.passed = True
            row.rubric_version = rubric_version
            row.judge_model = "judge-stub"
            row.subscores_json = {"coverage": row.score}
            session.commit()
            session.refresh(row)
            return row

    monkeypatch.setattr(benchmark_execution_adapter.BenchmarkExecutionAdapter, "run_sync", fake_run_sync)
    monkeypatch.setattr(benchmark_quality_service.BenchmarkQualityService, "evaluate_and_persist", fake_quality_persist)

    with TestClient(app) as client:
        corpus_response = client.post(
            "/api/internal-data/load",
            json={"source_type": "wiki", "wiki": {"source_id": "all"}},
        )
        assert corpus_response.status_code == 200
        assert corpus_response.json() == {
            "status": "success",
            "source_type": "wiki",
            "documents_loaded": 1,
            "chunks_created": 2,
        }

        create_response = client.post(
            "/api/benchmarks/runs",
            json={
                "dataset_id": "internal_v1",
                "modes": [
                    BenchmarkMode.baseline_retrieve_then_answer.value,
                    BenchmarkMode.agentic_default.value,
                ],
                "metadata": {"trigger": "e2e-acceptance"},
            },
        )
        assert create_response.status_code == 200
        run_id = create_response.json()["run_id"]

        detail = _poll_status(client, run_id)
        assert detail["status"] == "completed"
        assert detail["dataset_id"] == "internal_v1"
        assert detail["completed_questions"] == detail["total_questions"]
        assert detail["completed_questions"] > 0
        assert len(detail["mode_summaries"]) == 2

        compare_response = client.get(f"/api/benchmarks/runs/{run_id}/compare")
        assert compare_response.status_code == 200
        compare_body = compare_response.json()
        assert compare_body["run_id"] == run_id
        assert compare_body["baseline_mode"] == BenchmarkMode.baseline_retrieve_then_answer.value
        assert len(compare_body["comparisons"]) == 2

        list_response = client.get("/api/benchmarks/runs")
        assert list_response.status_code == 200
        listed_ids = {item["run_id"] for item in list_response.json()["runs"]}
        assert run_id in listed_ids

    _clear_state()


def test_benchmark_pipeline_rejects_invalid_mode_request() -> None:
    _clear_state()
    with TestClient(app) as client:
        response = client.post(
            "/api/benchmarks/runs",
            json={"dataset_id": "internal_v1", "modes": ["not_a_real_mode"]},
        )
    assert response.status_code == 422
    assert "Unsupported benchmark modes" in str(response.json())
    _clear_state()


def test_benchmark_pipeline_dataset_missing_sets_job_error_and_detail_404(monkeypatch) -> None:
    _clear_state()
    monkeypatch.setattr(benchmark_jobs, "_EXECUTOR", _InlineExecutor())
    monkeypatch.setattr(benchmark_jobs, "_build_runtime_dependencies", lambda: (object(), "model-test"))

    with TestClient(app) as client:
        create_response = client.post(
            "/api/benchmarks/runs",
            json={"dataset_id": "missing_dataset_id", "modes": [BenchmarkMode.agentic_default.value]},
        )
        assert create_response.status_code == 200
        run_id = create_response.json()["run_id"]

        with benchmark_jobs._JOB_LOCK:
            matched = [job for job in benchmark_jobs._JOBS.values() if job.run_id == run_id]
        assert len(matched) == 1
        assert matched[0].status == "error"
        assert "Benchmark dataset not found" in (matched[0].error or "")

        detail_response = client.get(f"/api/benchmarks/runs/{run_id}")
        assert detail_response.status_code == 404
        assert detail_response.json() == {"detail": "Benchmark run not found."}

    _clear_state()


def test_benchmark_pipeline_records_judge_timeout_and_failure_as_non_fatal(
    monkeypatch,
    caplog,
) -> None:
    _clear_state()
    caplog.set_level("INFO")
    monkeypatch.setattr(benchmark_jobs, "_EXECUTOR", _InlineExecutor())
    monkeypatch.setattr(benchmark_jobs, "_build_runtime_dependencies", lambda: (object(), "model-test"))
    monkeypatch.setattr(
        benchmark_execution_adapter.BenchmarkExecutionAdapter,
        "run_sync",
        lambda self, query, *, vector_store, model, config=None: RuntimeAgentRunResponse(  # noqa: ANN001
            output=f"answer::{query}",
            final_citations=[],
        ),
    )

    call_counter = {"count": 0}

    def fake_quality_failure(  # noqa: PLR0913
        self,
        *,
        result_id: int,
        question_text: str,
        expected_answer_points: list[str],
        required_sources: list[str],
        run_metadata=None,  # noqa: ANN001
        rubric_version: str = "v1",
        pass_threshold=None,  # noqa: ANN001
    ):
        del self, result_id, question_text, expected_answer_points, required_sources, run_metadata, rubric_version, pass_threshold
        call_counter["count"] += 1
        if call_counter["count"] % 2 == 0:
            raise RuntimeError("judge failed to parse response")
        raise TimeoutError("judge timeout after 30s")

    monkeypatch.setattr(benchmark_quality_service.BenchmarkQualityService, "evaluate_and_persist", fake_quality_failure)

    with TestClient(app) as client:
        create_response = client.post(
            "/api/benchmarks/runs",
            json={"dataset_id": "internal_v1", "modes": [BenchmarkMode.agentic_default.value]},
        )
        assert create_response.status_code == 200
        run_id = create_response.json()["run_id"]

        detail = _poll_status(client, run_id)
        assert detail["status"] == "completed"
        quality_errors = [
            item["quality"]["error"]
            for item in detail["results"]
            if item.get("quality") is not None and item["quality"].get("error")
        ]
        assert quality_errors
        assert any("judge timeout" in error for error in quality_errors)
        assert "judge failed to parse response" in caplog.text

    _clear_state()


def test_benchmark_pipeline_cancel_marks_run_and_job_as_cancelling() -> None:
    _clear_state()
    run_id = "run-cancel-e2e"
    with SessionLocal() as session:
        session.add(
            BenchmarkRun(
                run_id=run_id,
                status="running",
                dataset_id="internal_v1",
                slo_snapshot={},
                context_fingerprint="ctx-cancel",
                corpus_hash="hash-cancel",
                objective_snapshot={},
                run_metadata={},
            )
        )
        session.add(BenchmarkRunMode(run_id=run_id, mode=BenchmarkMode.agentic_default.value, mode_metadata={}))
        session.commit()

    with benchmark_jobs._JOB_LOCK:
        benchmark_jobs._JOBS["job-cancel-e2e"] = benchmark_jobs.BenchmarkRunJobStatus(
            job_id="job-cancel-e2e",
            run_id=run_id,
            status="running",
        )

    with TestClient(app) as client:
        cancel_response = client.post(f"/api/benchmarks/runs/{run_id}/cancel")
        assert cancel_response.status_code == 200
        assert cancel_response.json() == {"status": "success", "message": "Cancellation requested."}

        detail_response = client.get(f"/api/benchmarks/runs/{run_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["status"] == "cancelling"

    with benchmark_jobs._JOB_LOCK:
        job = benchmark_jobs._JOBS["job-cancel-e2e"]
        assert job.cancel_requested is True
        assert job.status == "cancelling"

    _clear_state()
