from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models import BenchmarkQualityScore, BenchmarkResult, BenchmarkRun, BenchmarkRunMode
from schemas import BenchmarkMode, CitationSourceRow, RuntimeAgentRunResponse
from services.benchmark_runner import BenchmarkRunner

DATABASE_URL = "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search"

def _write_dataset(tmp_path: Path, dataset_id: str) -> Path:
    dataset_dir = tmp_path / "benchmarks" / "datasets" / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = dataset_dir / "questions.jsonl"
    rows = [
        {
            "question_id": "DRB-001",
            "question": "What is the first benchmark question?",
            "domain": "policy",
            "difficulty": "easy",
            "expected_answer_points": ["point-a"],
            "required_sources": ["source-a"],
            "disallowed_behaviors": ["hallucinate"],
        },
        {
            "question_id": "DRB-002",
            "question": "What is the second benchmark question?",
            "domain": "policy",
            "difficulty": "medium",
            "expected_answer_points": ["point-b"],
            "required_sources": ["source-b"],
            "disallowed_behaviors": ["hallucinate"],
        },
    ]
    with dataset_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    return tmp_path / "benchmarks" / "datasets"


class _SuccessAdapter:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def run_sync(self, query: str, *, vector_store, model, config=None):  # noqa: ANN001
        self.calls.append({"query": query, "model": model, "config": config})
        return RuntimeAgentRunResponse(
            output=f"answer::{query}",
            final_citations=[CitationSourceRow(citation_index=1, rank=1, title="Doc", source="internal")],
        )


class _FailOnceAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def run_sync(self, query: str, *, vector_store, model, config=None):  # noqa: ANN001
        self.calls += 1
        if self.calls == 2:
            raise RuntimeError("simulated adapter failure")
        return RuntimeAgentRunResponse(output=f"ok::{query}", final_citations=[])


class _RecoverAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def run_sync(self, query: str, *, vector_store, model, config=None):  # noqa: ANN001
        self.calls += 1
        return RuntimeAgentRunResponse(output=f"recovered::{query}", final_citations=[])


class _QualityServiceStub:
    def __init__(self, *, session_factory, fail_on_question: str | None = None):  # noqa: ANN001
        self._session_factory = session_factory
        self._fail_on_question = fail_on_question
        self.calls: list[int] = []
        self.metadata_calls: list[dict[str, object] | None] = []

    def evaluate_and_persist(  # noqa: PLR0913
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
        del expected_answer_points, required_sources, pass_threshold
        self.calls.append(result_id)
        self.metadata_calls.append(run_metadata if isinstance(run_metadata, dict) else None)
        if self._fail_on_question and self._fail_on_question == question_text:
            raise RuntimeError("simulated quality evaluator failure")

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
            row.score = 0.9
            row.passed = True
            row.rubric_version = rubric_version
            row.judge_model = "quality-stub"
            row.subscores_json = {"coverage": 0.9}
            session.commit()
            session.refresh(row)
            return row


def test_runner_executes_mode_by_question_and_persists_results(tmp_path: Path) -> None:
    dataset_root = _write_dataset(tmp_path, "tiny_v1")
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    adapter = _SuccessAdapter()
    quality_service = _QualityServiceStub(session_factory=session_factory)
    runner = BenchmarkRunner(
        session_factory=session_factory,
        execution_adapter=adapter,
        quality_service=quality_service,
        dataset_root=dataset_root,
    )
    run_id = f"run-benchmark-1-{uuid.uuid4()}"

    summary = runner.run(
        run_id=run_id,
        dataset_id="tiny_v1",
        modes=[BenchmarkMode.agentic_default, BenchmarkMode.agentic_no_rerank],
        vector_store=object(),
        model="model-test",
        metadata={"trigger": "test"},
    )

    assert summary.run_id == run_id
    assert summary.mode_count == 2
    assert summary.question_count == 2
    assert summary.completed_results == 4
    assert len(adapter.calls) == 4
    assert len(quality_service.calls) == 4
    assert all(isinstance(metadata, dict) for metadata in quality_service.metadata_calls)
    assert all(metadata.get("run_id") == run_id for metadata in quality_service.metadata_calls if metadata is not None)
    assert all(metadata.get("mode") in {BenchmarkMode.agentic_default.value, BenchmarkMode.agentic_no_rerank.value} for metadata in quality_service.metadata_calls if metadata is not None)
    assert all(metadata.get("question_id") in {"DRB-001", "DRB-002"} for metadata in quality_service.metadata_calls if metadata is not None)

    with Session(engine) as session:
        run = session.get(BenchmarkRun, run_id)
        assert run is not None
        assert run.status == "completed"
        assert run.started_at is not None
        assert run.finished_at is not None

        modes = session.scalars(select(BenchmarkRunMode).where(BenchmarkRunMode.run_id == run_id)).all()
        assert sorted(item.mode for item in modes) == [
            BenchmarkMode.agentic_default.value,
            BenchmarkMode.agentic_no_rerank.value,
        ]

        results = session.scalars(select(BenchmarkResult).where(BenchmarkResult.run_id == run_id)).all()
        assert len(results) == 4
        assert all(row.execution_error is None for row in results)
        assert all(row.latency_ms is not None for row in results)
        quality_scores = session.scalars(select(BenchmarkQualityScore).where(BenchmarkQualityScore.run_id == run_id)).all()
        assert len(quality_scores) == 4
        assert all(row.score == 0.9 for row in quality_scores)
        assert {
            (row.run_id, row.mode, row.question_id)
            for row in quality_scores
        } == {
            (run_id, BenchmarkMode.agentic_default.value, "DRB-001"),
            (run_id, BenchmarkMode.agentic_default.value, "DRB-002"),
            (run_id, BenchmarkMode.agentic_no_rerank.value, "DRB-001"),
            (run_id, BenchmarkMode.agentic_no_rerank.value, "DRB-002"),
        }


def test_runner_persists_partial_progress_and_resumes_failed_questions_only(tmp_path: Path) -> None:
    dataset_root = _write_dataset(tmp_path, "tiny_v1")
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    fail_adapter = _FailOnceAdapter()
    quality_service = _QualityServiceStub(session_factory=session_factory)
    runner = BenchmarkRunner(
        session_factory=session_factory,
        execution_adapter=fail_adapter,
        quality_service=quality_service,
        dataset_root=dataset_root,
    )
    run_id = f"run-benchmark-2-{uuid.uuid4()}"

    try:
        runner.run(
            run_id=run_id,
            dataset_id="tiny_v1",
            modes=[BenchmarkMode.agentic_default],
            vector_store=object(),
            model="model-test",
        )
        assert False, "Expected runner to raise after adapter failure"
    except RuntimeError as exc:
        assert "simulated adapter failure" in str(exc)

    with Session(engine) as session:
        run = session.get(BenchmarkRun, run_id)
        assert run is not None
        assert run.status == "failed"
        assert run.error is not None

        results = session.scalars(select(BenchmarkResult).where(BenchmarkResult.run_id == run_id)).all()
        assert len(results) == 2
        by_question = {row.question_id: row for row in results}
        assert by_question["DRB-001"].execution_error is None
        assert by_question["DRB-002"].execution_error == "simulated adapter failure"

    recover_adapter = _RecoverAdapter()
    resume_runner = BenchmarkRunner(
        session_factory=session_factory,
        execution_adapter=recover_adapter,
        quality_service=quality_service,
        dataset_root=dataset_root,
    )
    summary = resume_runner.run(
        run_id=run_id,
        dataset_id="tiny_v1",
        modes=[BenchmarkMode.agentic_default],
        vector_store=object(),
        model="model-test",
    )

    assert summary.completed_results == 1
    assert recover_adapter.calls == 1

    with Session(engine) as session:
        run = session.get(BenchmarkRun, run_id)
        assert run is not None
        assert run.status == "completed"
        assert run.error is None

        results = session.scalars(select(BenchmarkResult).where(BenchmarkResult.run_id == run_id)).all()
        assert len(results) == 2
        assert all(row.execution_error is None for row in results)


def test_runner_captures_quality_failures_as_non_fatal_errors(tmp_path: Path) -> None:
    dataset_root = _write_dataset(tmp_path, "tiny_v1")
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    adapter = _SuccessAdapter()
    quality_service = _QualityServiceStub(
        session_factory=session_factory,
        fail_on_question="What is the second benchmark question?",
    )
    runner = BenchmarkRunner(
        session_factory=session_factory,
        execution_adapter=adapter,
        quality_service=quality_service,
        dataset_root=dataset_root,
    )
    run_id = f"run-benchmark-quality-nonfatal-{uuid.uuid4()}"

    summary = runner.run(
        run_id=run_id,
        dataset_id="tiny_v1",
        modes=[BenchmarkMode.agentic_default],
        vector_store=object(),
        model="model-test",
    )

    assert summary.completed_results == 2
    assert len(quality_service.calls) == 2

    with Session(engine) as session:
        run = session.get(BenchmarkRun, run_id)
        assert run is not None
        assert run.status == "completed"
        metadata = run.run_metadata or {}
        assert isinstance(metadata.get("evaluation_errors"), list)
        assert len(metadata["evaluation_errors"]) == 1
        assert metadata["evaluation_errors"][0]["stage"] == "quality"
        assert metadata["evaluation_errors"][0]["mode"] == BenchmarkMode.agentic_default.value
        assert metadata["evaluation_errors"][0]["question_id"] == "DRB-002"
        assert "simulated quality evaluator failure" in metadata["evaluation_errors"][0]["error"]

        results = session.scalars(select(BenchmarkResult).where(BenchmarkResult.run_id == run_id)).all()
        assert len(results) == 2
        assert all(row.execution_error is None for row in results)

        quality_scores = session.scalars(select(BenchmarkQualityScore).where(BenchmarkQualityScore.run_id == run_id)).all()
        assert len(quality_scores) == 1
        assert quality_scores[0].question_id == "DRB-001"


def test_runner_emits_langfuse_benchmark_trace_hooks(tmp_path: Path, monkeypatch) -> None:
    dataset_root = _write_dataset(tmp_path, "tiny_v1")
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    adapter = _SuccessAdapter()
    quality_service = _QualityServiceStub(session_factory=session_factory)
    runner = BenchmarkRunner(
        session_factory=session_factory,
        execution_adapter=adapter,
        quality_service=quality_service,
        dataset_root=dataset_root,
    )
    run_id = f"run-benchmark-langfuse-{uuid.uuid4()}"
    captured: dict[str, list[dict[str, object]]] = {"traces": [], "spans": [], "scores": [], "ends": []}

    import services.benchmark_runner as benchmark_runner_module

    monkeypatch.setattr(
        benchmark_runner_module,
        "start_langfuse_trace",
        lambda **kwargs: captured["traces"].append(kwargs) or object(),
    )
    monkeypatch.setattr(
        benchmark_runner_module,
        "start_langfuse_span",
        lambda **kwargs: captured["spans"].append(kwargs) or object(),
    )
    monkeypatch.setattr(
        benchmark_runner_module,
        "record_langfuse_score",
        lambda **kwargs: captured["scores"].append(kwargs),
    )
    monkeypatch.setattr(
        benchmark_runner_module,
        "end_langfuse_observation",
        lambda observation, **kwargs: captured["ends"].append(kwargs),
    )

    summary = runner.run(
        run_id=run_id,
        dataset_id="tiny_v1",
        modes=[BenchmarkMode.agentic_default],
        vector_store=object(),
        model="model-test",
    )

    assert summary.completed_results == 2
    assert captured["traces"]
    assert any(item["name"] == "benchmark.run" for item in captured["traces"])
    assert any(item["name"] == "benchmark.dataset_load" for item in captured["spans"])
    assert any(item["name"] == "benchmark.mode_execution" for item in captured["spans"])
    assert any(item["name"] == "benchmark.question_execution" for item in captured["spans"])
    assert any(item["name"] == "benchmark.correctness" for item in captured["scores"])
    assert any(item["name"] == "benchmark.latency_ms" for item in captured["scores"])
    assert captured["ends"]
