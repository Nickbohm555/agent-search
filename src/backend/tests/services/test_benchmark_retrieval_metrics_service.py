from __future__ import annotations

import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models import BenchmarkResult, BenchmarkRetrievalMetric, BenchmarkRun
from services.benchmark_retrieval_metrics_service import BenchmarkRetrievalMetricsService

DATABASE_URL = "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search"


def _create_run_and_result(
    session: Session,
    *,
    run_id: str,
    question_id: str,
    citations: list[dict[str, object]],
    run_metadata: dict[str, object] | None = None,
) -> int:
    run = BenchmarkRun(
        run_id=run_id,
        status="completed",
        dataset_id="internal_v1",
        slo_snapshot={"max_latency_ms_p95": 30000, "min_correctness": 0.75},
        context_fingerprint=f"fingerprint-{run_id}",
        corpus_hash=f"corpus-{run_id}",
        objective_snapshot={"primary_kpi": "correctness"},
        run_metadata=run_metadata or {},
    )
    session.add(run)
    session.flush()
    row = BenchmarkResult(
        run_id=run_id,
        mode="agentic_default",
        question_id=question_id,
        answer_payload={"output": "answer"},
        citations=citations,
    )
    session.add(row)
    session.commit()
    return row.id


def test_retrieval_metrics_service_evaluates_ranked_signals() -> None:
    service = BenchmarkRetrievalMetricsService()

    evaluation = service.evaluate(
        citations=[
            {"rank": 1, "document_id": "doc-a"},
            {"rank": 2, "document_id": "doc-b"},
            {"rank": 3, "document_id": "doc-c"},
        ],
        relevant_document_ids=["doc-b", "doc-z"],
        k=2,
        label_source="test",
    )

    assert evaluation.recall_at_k == 0.5
    assert evaluation.mrr == 0.5
    assert round(evaluation.ndcg or 0.0, 6) == 0.386853
    assert evaluation.retrieved_document_ids == ["doc-a", "doc-b", "doc-c"]
    assert evaluation.relevant_document_ids == ["doc-b", "doc-z"]
    assert evaluation.k == 2
    assert evaluation.label_source == "test"


def test_retrieval_metrics_service_persists_and_updates_from_run_metadata_labels() -> None:
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    run_id = f"run-retrieval-{uuid.uuid4()}"

    with Session(engine) as session:
        result_id = _create_run_and_result(
            session,
            run_id=run_id,
            question_id="DRB-001",
            citations=[
                {"rank": 1, "document_id": "doc-x"},
                {"rank": 2, "document_id": "doc-gold"},
                {"rank": 3, "document_id": "doc-y"},
            ],
            run_metadata={
                "retrieval_labels": {
                    "DRB-001": {"relevant_document_ids": ["doc-gold", "doc-other"]},
                }
            },
        )

    service = BenchmarkRetrievalMetricsService(session_factory=session_factory, default_k=3)
    first = service.evaluate_and_persist(result_id=result_id)
    assert first.recall_at_k == 0.5
    assert first.mrr == 0.5
    assert round(first.ndcg or 0.0, 6) == 0.386853
    assert first.k == 3
    assert first.retrieved_document_ids == ["doc-x", "doc-gold", "doc-y"]
    assert first.relevant_document_ids == ["doc-gold", "doc-other"]
    assert first.label_source == "run_metadata"

    second = service.evaluate_and_persist(
        result_id=result_id,
        relevant_document_ids=["doc-x"],
        k=1,
        label_source="manual",
    )
    assert second.id == first.id
    assert second.recall_at_k == 1.0
    assert second.mrr == 1.0
    assert second.ndcg == 1.0
    assert second.k == 1
    assert second.relevant_document_ids == ["doc-x"]
    assert second.label_source == "manual"

    with Session(engine) as session:
        rows = session.scalars(
            select(BenchmarkRetrievalMetric).where(BenchmarkRetrievalMetric.run_id == run_id)
        ).all()
        assert len(rows) == 1
        assert rows[0].result_id == result_id


def test_retrieval_metrics_service_persists_retrieved_ids_without_labels() -> None:
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    run_id = f"run-retrieval-unlabeled-{uuid.uuid4()}"

    with Session(engine) as session:
        result_id = _create_run_and_result(
            session,
            run_id=run_id,
            question_id="DRB-002",
            citations=[
                {"rank": 1, "document_id": "doc-a"},
                {"rank": 2, "document_id": "doc-a"},
                {"rank": 3, "document_id": "doc-b"},
                {"document_id": "doc-c"},
            ],
        )

    service = BenchmarkRetrievalMetricsService(session_factory=session_factory)
    row = service.evaluate_and_persist(result_id=result_id, k=5)

    assert row.recall_at_k is None
    assert row.mrr is None
    assert row.ndcg is None
    assert row.retrieved_document_ids == ["doc-a", "doc-b", "doc-c"]
    assert row.relevant_document_ids == []
    assert row.label_source is None
