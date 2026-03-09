import sys
from types import SimpleNamespace
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db import get_db
from routers.agent import router as agent_router


def test_post_run_returns_response_shape_from_runtime_agent(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    from schemas import RuntimeAgentRunResponse, SubQuestionAnswer
    from routers import agent as agent_router_module

    captured: dict[str, object] = {}

    def fake_run_runtime_agent(payload, db):
        captured["query"] = payload.query
        assert isinstance(db, Session)
        return RuntimeAgentRunResponse(
            main_question=payload.query,
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="What changed in policy X?",
                    sub_answer="Policy X was revised in January 2026.",
                    tool_call_input='{"query":"What changed in policy X?"}',
                    sub_agent_response="I reviewed the latest policy notes and summarized the change.",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                )
            ],
            output=f"Echo: {payload.query}",
        )

    monkeypatch.setattr(agent_router_module, "run_runtime_agent", fake_run_runtime_agent)

    app = FastAPI()
    app.include_router(agent_router)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.post("/api/agents/run", json={"query": "Find Hormuz risks"})
    assert response.status_code == 200
    assert response.json() == {
        "main_question": "Find Hormuz risks",
        "sub_qa": [
            {
                "sub_question": "What changed in policy X?",
                "sub_answer": "Policy X was revised in January 2026.",
                "tool_call_input": '{"query":"What changed in policy X?"}',
                "expanded_query": "",
                "sub_agent_response": "I reviewed the latest policy notes and summarized the change.",
                "answerable": True,
                "verification_reason": "grounded_in_reranked_documents",
            }
        ],
        "output": "Echo: Find Hormuz risks",
    }
    assert captured["query"] == "Find Hormuz risks"


def test_post_run_async_returns_job_start_shape(monkeypatch) -> None:
    from routers import agent as agent_router_module

    def fake_start_agent_run_job(payload):
        assert payload.query == "Show me async flow"
        return SimpleNamespace(job_id="job-123", run_id="run-123", status="running")

    monkeypatch.setattr(agent_router_module, "start_agent_run_job", fake_start_agent_run_job)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post("/api/agents/run-async", json={"query": "Show me async flow"})
    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-123",
        "run_id": "run-123",
        "status": "running",
    }


def test_get_run_status_returns_subquestions_before_final_completion(monkeypatch) -> None:
    from routers import agent as agent_router_module
    from schemas import AgentRunStageMetadata, SubQuestionAnswer

    def fake_get_agent_run_job(job_id):
        assert job_id == "job-123"
        return SimpleNamespace(
            job_id="job-123",
            run_id="run-123",
            status="running",
            message="Stage completed: subquestions_ready",
            stage="subquestions_ready",
            stages=[
                AgentRunStageMetadata(
                    stage="subquestions_ready",
                    status="completed",
                    sub_question="",
                    lane_index=0,
                    lane_total=2,
                    emitted_at=123.0,
                )
            ],
            decomposition_sub_questions=["First question?", "Second question?"],
            sub_question_artifacts=[],
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="First question?",
                    sub_answer="",
                )
            ],
            output="",
            result=None,
            error=None,
            cancel_requested=False,
        )

    monkeypatch.setattr(agent_router_module, "get_agent_run_job", fake_get_agent_run_job)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.get("/api/agents/run-status/job-123")
    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-123",
        "run_id": "run-123",
        "status": "running",
        "message": "Stage completed: subquestions_ready",
        "stage": "subquestions_ready",
        "stages": [
            {
                "stage": "subquestions_ready",
                "status": "completed",
                "sub_question": "",
                "lane_index": 0,
                "lane_total": 2,
                "emitted_at": 123.0,
            }
        ],
        "decomposition_sub_questions": ["First question?", "Second question?"],
        "sub_question_artifacts": [],
        "sub_qa": [
            {
                "sub_question": "First question?",
                "sub_answer": "",
                "tool_call_input": "",
                "expanded_query": "",
                "sub_agent_response": "",
                "answerable": False,
                "verification_reason": "",
            }
        ],
        "output": "",
        "result": None,
        "error": None,
        "cancel_requested": False,
    }


def test_post_run_cancel_returns_success(monkeypatch) -> None:
    from routers import agent as agent_router_module

    monkeypatch.setattr(agent_router_module, "cancel_agent_run_job", lambda _job_id: True)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post("/api/agents/run-cancel/job-123")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Cancellation requested."}
