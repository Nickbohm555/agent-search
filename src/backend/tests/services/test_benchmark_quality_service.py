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

from config import BenchmarkRuntimeSettings
from models import BenchmarkQualityScore, BenchmarkResult, BenchmarkRun
from services.benchmark_quality_service import BenchmarkQualityService

DATABASE_URL = "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search"


def _create_run_and_result(session: Session, *, run_id: str, answer_text: str, question_id: str = "DRB-001") -> int:
    run = BenchmarkRun(
        run_id=run_id,
        status="completed",
        dataset_id="internal_v1",
        slo_snapshot={"max_latency_ms_p95": 30000, "min_correctness": 0.75},
        context_fingerprint=f"fingerprint-{run_id}",
        corpus_hash=f"corpus-{run_id}",
        objective_snapshot={"primary_kpi": "correctness"},
        run_metadata={"trigger": "quality_test"},
    )
    session.add(run)
    session.flush()
    row = BenchmarkResult(
        run_id=run_id,
        mode="agentic_default",
        question_id=question_id,
        answer_payload={"output": answer_text},
        citations=[{"citation_index": 1, "title": "Doc", "source": "internal"}],
    )
    session.add(row)
    session.commit()
    return row.id


def test_quality_service_evaluates_with_deterministic_openai_rubric_output() -> None:
    class _FakeResponse:
        content = json.dumps(
            {
                "score": 0.8,
                "rationale": "Most expected points are covered.",
                "subscores": {"coverage": 0.8, "grounding": 0.9},
            }
        )

    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            assert model == "gpt-test-judge"
            assert temperature == 0.0

        def invoke(self, prompt: str):
            assert "Rubric instructions:" in prompt
            assert "expected_answer_points" in prompt
            return _FakeResponse()

    service = BenchmarkQualityService(
        runtime_settings=BenchmarkRuntimeSettings.from_env({"BENCHMARK_JUDGE_MODEL": "gpt-test-judge"}),
        llm_factory=_FakeChatOpenAI,
    )
    evaluation = service.evaluate(
        question_text="What changed in policy?",
        answer_payload={"output": "Policy changed in 2025 with source support."},
        expected_answer_points=["policy changed in 2025", "source support"],
        required_sources=["source-a"],
    )

    assert evaluation.score == 0.8
    assert evaluation.passed is True
    assert evaluation.rubric_version == "v1"
    assert evaluation.judge_model == "gpt-test-judge"
    assert evaluation.subscores == {"coverage": 0.8, "grounding": 0.9}


def test_quality_service_persists_and_updates_quality_scores() -> None:
    class _FakeResponse:
        def __init__(self, content: str) -> None:
            self.content = content

    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            self.calls = 0
            assert model == "gpt-test-judge"
            assert temperature == 0.0

        def invoke(self, prompt: str):
            self.calls += 1
            if self.calls == 1:
                return _FakeResponse(
                    '```json\n{"score":0.60,"rationale":"partial","subscores":{"coverage":0.60}}\n```'
                )
            return _FakeResponse(
                json.dumps(
                    {
                        "score": 0.95,
                        "rationale": "fully grounded",
                        "subscores": {"coverage": 0.95, "grounding": 0.96},
                    }
                )
            )

    fake_llm = _FakeChatOpenAI(model="gpt-test-judge", temperature=0.0)
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    run_id = f"run-quality-{uuid.uuid4()}"

    with Session(engine) as session:
        result_id = _create_run_and_result(
            session,
            run_id=run_id,
            answer_text="Policy changed with partial support.",
        )

    service = BenchmarkQualityService(
        session_factory=session_factory,
        runtime_settings=BenchmarkRuntimeSettings.from_env(
            {"BENCHMARK_JUDGE_MODEL": "gpt-test-judge", "BENCHMARK_TARGET_MIN_CORRECTNESS": "0.75"}
        ),
        llm_factory=lambda **_: fake_llm,
    )

    first_row = service.evaluate_and_persist(
        result_id=result_id,
        question_text="What changed in policy?",
        expected_answer_points=["policy changed", "grounded support"],
        required_sources=["source-a"],
    )
    assert first_row.score == 0.60
    assert first_row.passed is False
    assert first_row.subscores_json == {"coverage": 0.6}

    second_row = service.evaluate_and_persist(
        result_id=result_id,
        question_text="What changed in policy?",
        expected_answer_points=["policy changed", "grounded support"],
        required_sources=["source-a"],
    )
    assert second_row.id == first_row.id
    assert second_row.score == 0.95
    assert second_row.passed is True
    assert second_row.subscores_json == {"coverage": 0.95, "grounding": 0.96}

    with Session(engine) as session:
        rows = session.scalars(
            select(BenchmarkQualityScore).where(BenchmarkQualityScore.run_id == run_id)
        ).all()
        assert len(rows) == 1
        assert rows[0].result_id == result_id


def test_quality_service_emits_langfuse_judge_hooks(monkeypatch) -> None:
    captured: dict[str, list[dict[str, object]]] = {"traces": [], "spans": [], "scores": [], "ends": []}

    import services.benchmark_quality_service as benchmark_quality_module

    monkeypatch.setattr(
        benchmark_quality_module,
        "start_langfuse_trace",
        lambda **kwargs: captured["traces"].append(kwargs) or object(),
    )
    monkeypatch.setattr(
        benchmark_quality_module,
        "start_langfuse_span",
        lambda **kwargs: captured["spans"].append(kwargs) or object(),
    )
    monkeypatch.setattr(
        benchmark_quality_module,
        "record_langfuse_score",
        lambda **kwargs: captured["scores"].append(kwargs),
    )
    monkeypatch.setattr(
        benchmark_quality_module,
        "end_langfuse_observation",
        lambda observation, **kwargs: captured["ends"].append(kwargs),
    )

    class _FakeResponse:
        content = '{"score": 0.81, "rationale": "grounded", "subscores": {"coverage": 0.81}}'

    class _FakeChatOpenAI:
        def __init__(self, model: str, temperature: float) -> None:
            assert model == "gpt-test-judge"
            assert temperature == 0.0

        def invoke(self, prompt: str):
            return _FakeResponse()

    service = BenchmarkQualityService(
        runtime_settings=BenchmarkRuntimeSettings.from_env({"BENCHMARK_JUDGE_MODEL": "gpt-test-judge"}),
        llm_factory=_FakeChatOpenAI,
    )
    evaluation = service.evaluate(
        question_text="What changed in policy?",
        answer_payload={"output": "Policy changed in 2025."},
        expected_answer_points=["policy changed"],
        required_sources=["source-a"],
        run_metadata={"run_id": "run-1", "mode": "agentic_default", "question_id": "DRB-001"},
    )

    assert evaluation.score == 0.81
    assert captured["traces"]
    assert any(item["name"] == "benchmark.judge" for item in captured["traces"])
    assert any(item["name"] == "benchmark.judge_scoring" for item in captured["spans"])
    assert any(item["name"] == "benchmark.correctness" for item in captured["scores"])
    assert captured["ends"]
