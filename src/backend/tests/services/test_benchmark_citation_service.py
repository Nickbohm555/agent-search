from __future__ import annotations

import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models import BenchmarkCitationScore, BenchmarkCitationVerification, BenchmarkResult, BenchmarkRun
from services.benchmark_citation_service import BenchmarkCitationService

DATABASE_URL = "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search"


def _create_run_and_result(session: Session, *, run_id: str, answer_text: str) -> int:
    run = BenchmarkRun(
        run_id=run_id,
        status="completed",
        dataset_id="internal_v1",
        slo_snapshot={"max_latency_ms_p95": 30000, "min_correctness": 0.75},
        context_fingerprint=f"fingerprint-{run_id}",
        corpus_hash=f"corpus-{run_id}",
        objective_snapshot={"primary_kpi": "correctness"},
        run_metadata={"trigger": "citation_test"},
    )
    session.add(run)
    session.flush()
    row = BenchmarkResult(
        run_id=run_id,
        mode="agentic_default",
        question_id="DRB-001",
        answer_payload={"output": answer_text},
        citations=[
            {
                "citation_index": 1,
                "title": "Policy Update 2025",
                "source": "public-report",
                "content": "The policy changed in 2025 and introduced a new emissions cap.",
            },
            {
                "citation_index": 2,
                "title": "Budget Summary",
                "source": "finance-brief",
                "content": "Funding increased for implementation planning only.",
            },
        ],
    )
    session.add(row)
    session.commit()
    return row.id


def test_citation_service_evaluates_presence_and_support_rates() -> None:
    service = BenchmarkCitationService()

    evaluation = service.evaluate(
        answer_payload={"output": "Policy changed in 2025 [1]. It reduced emissions quickly [2]. Extra claim [3]."},
        citations=[
            {
                "citation_index": 1,
                "title": "Policy Update 2025",
                "source": "public-report",
                "content": "The policy changed in 2025 and introduced a new emissions cap.",
            },
            {
                "citation_index": 2,
                "title": "Budget Summary",
                "source": "finance-brief",
                "content": "Funding increased for implementation planning only.",
            },
        ],
    )

    assert evaluation.total_citation_count == 3
    assert evaluation.found_citation_count == 2
    assert evaluation.supported_citation_count == 1
    assert evaluation.citation_presence_rate == 2 / 3
    assert evaluation.basic_support_rate == 1 / 2
    assert [item.support_label for item in evaluation.verifications] == [
        "supported",
        "unsupported",
        "missing_context",
    ]


def test_citation_service_persists_and_replaces_verification_rows() -> None:
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    run_id = f"run-citation-{uuid.uuid4()}"

    with Session(engine) as session:
        result_id = _create_run_and_result(
            session,
            run_id=run_id,
            answer_text="Policy changed in 2025 [1]. It reduced emissions quickly [2]. Extra claim [3].",
        )

    service = BenchmarkCitationService(session_factory=session_factory)

    first = service.evaluate_and_persist(result_id=result_id)
    assert first.citation_presence_rate == 2 / 3
    assert first.basic_support_rate == 1 / 2

    with Session(engine) as session:
        result = session.get(BenchmarkResult, result_id)
        assert result is not None
        result.answer_payload = {"output": "Policy changed in 2025 [1]."}
        session.commit()

    second = service.evaluate_and_persist(result_id=result_id)
    assert second.id == first.id
    assert second.citation_presence_rate == 1.0
    assert second.basic_support_rate == 1.0

    with Session(engine) as session:
        stored_scores = session.scalars(
            select(BenchmarkCitationScore).where(BenchmarkCitationScore.run_id == run_id)
        ).all()
        assert len(stored_scores) == 1
        assert stored_scores[0].result_id == result_id

        verifications = session.scalars(
            select(BenchmarkCitationVerification)
            .where(BenchmarkCitationVerification.run_id == run_id)
            .order_by(BenchmarkCitationVerification.id.asc())
        ).all()
        assert len(verifications) == 1
        assert verifications[0].citation_marker == "[1]"
        assert verifications[0].support_label == "supported"
