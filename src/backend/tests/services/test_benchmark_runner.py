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

from models import BenchmarkResult, BenchmarkRun, BenchmarkRunMode
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


def test_runner_executes_mode_by_question_and_persists_results(tmp_path: Path) -> None:
    dataset_root = _write_dataset(tmp_path, "tiny_v1")
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    adapter = _SuccessAdapter()
    runner = BenchmarkRunner(
        session_factory=session_factory,
        execution_adapter=adapter,
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


def test_runner_persists_partial_progress_and_resumes_failed_questions_only(tmp_path: Path) -> None:
    dataset_root = _write_dataset(tmp_path, "tiny_v1")
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    fail_adapter = _FailOnceAdapter()
    runner = BenchmarkRunner(
        session_factory=session_factory,
        execution_adapter=fail_adapter,
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
