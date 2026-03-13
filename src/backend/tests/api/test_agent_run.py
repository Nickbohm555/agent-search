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

from agent_search.errors import SDKConfigurationError
from db import get_db
from routers.agent import router as agent_router


def test_post_run_returns_server_generated_thread_id_when_request_omits_it(monkeypatch) -> None:
    from routers import agent as agent_router_module
    from schemas import RuntimeAgentRunResponse

    captured: dict[str, object] = {}
    generated_thread_id = "550e8400-e29b-41d4-a716-446655440111"

    def fake_sdk_run(query, *, vector_store, model, config=None):
        captured["query"] = query
        captured["vector_store"] = vector_store
        captured["model"] = model
        captured["config"] = config
        return RuntimeAgentRunResponse(
            main_question=query,
            thread_id=generated_thread_id,
            sub_qa=[],
            sub_answers=[],
            output=f"Echo: {query}",
        )

    monkeypatch.setattr(agent_router_module, "_build_sdk_runtime_dependencies", lambda: (object(), object()))
    monkeypatch.setattr(agent_router_module, "sdk_advanced_rag", fake_sdk_run)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post("/api/agents/run", json={"query": "Generate a thread id"})

    assert response.status_code == 200
    assert response.json()["thread_id"] == generated_thread_id
    assert captured["query"] == "Generate a thread id"
    assert captured["config"] is None


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
    sentinel_vector_store = object()
    sentinel_model = object()

    def fake_sdk_run(query, *, vector_store, model, config=None):
        captured["query"] = query
        captured["vector_store"] = vector_store
        captured["model"] = model
        captured["config"] = config
        return RuntimeAgentRunResponse(
            main_question=query,
            thread_id="550e8400-e29b-41d4-a716-446655440000",
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
            sub_answers=[
                SubQuestionAnswer(
                    sub_question="What changed in policy X?",
                    sub_answer="Policy X was revised in January 2026.",
                    tool_call_input='{"query":"What changed in policy X?"}',
                    sub_agent_response="I reviewed the latest policy notes and summarized the change.",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                )
            ],
            output=f"Echo: {query}",
        )

    monkeypatch.setattr(agent_router_module, "_build_sdk_runtime_dependencies", lambda: (sentinel_vector_store, sentinel_model))
    monkeypatch.setattr(agent_router_module, "sdk_advanced_rag", fake_sdk_run)

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

    response = client.post(
        "/api/agents/run",
        json={"query": "Find Hormuz risks", "thread_id": "550e8400-e29b-41d4-a716-446655440000"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "main_question": "Find Hormuz risks",
        "thread_id": "550e8400-e29b-41d4-a716-446655440000",
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
        "sub_answers": [
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
        "final_citations": [],
    }
    assert captured == {
        "query": "Find Hormuz risks",
        "vector_store": sentinel_vector_store,
        "model": sentinel_model,
        "config": {"thread_id": "550e8400-e29b-41d4-a716-446655440000"},
    }
    assert response.json()["sub_answers"] == response.json()["sub_qa"]


def test_post_run_async_returns_job_start_shape(monkeypatch) -> None:
    from routers import agent as agent_router_module
    from schemas import RuntimeAgentRunAsyncStartResponse

    captured: dict[str, object] = {}
    sentinel_vector_store = object()
    sentinel_model = object()

    def fake_sdk_run_async(query, *, vector_store, model, config=None):
        captured["query"] = query
        captured["vector_store"] = vector_store
        captured["model"] = model
        captured["config"] = config
        return RuntimeAgentRunAsyncStartResponse(
            job_id="job-123",
            run_id="run-123",
            thread_id="550e8400-e29b-41d4-a716-446655440000",
            status="running",
        )

    monkeypatch.setattr(agent_router_module, "_build_sdk_runtime_dependencies", lambda: (sentinel_vector_store, sentinel_model))
    monkeypatch.setattr(agent_router_module, "sdk_run_async", fake_sdk_run_async)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post(
        "/api/agents/run-async",
        json={"query": "Show me async flow", "thread_id": "550e8400-e29b-41d4-a716-446655440000"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-123",
        "run_id": "run-123",
        "thread_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "running",
    }
    assert captured == {
        "query": "Show me async flow",
        "vector_store": sentinel_vector_store,
        "model": sentinel_model,
        "config": {"thread_id": "550e8400-e29b-41d4-a716-446655440000"},
    }


def test_post_run_accepts_additive_controls_payload_without_breaking_legacy_forwarding(monkeypatch) -> None:
    from routers import agent as agent_router_module
    from schemas import RuntimeAgentRunResponse

    captured: dict[str, object] = {}

    def fake_sdk_run(query, *, vector_store, model, config=None):
        captured["query"] = query
        captured["config"] = config
        return RuntimeAgentRunResponse(
            main_question=query,
            thread_id="550e8400-e29b-41d4-a716-446655440010",
            sub_qa=[],
            sub_answers=[],
            output=f"Echo: {query}",
        )

    monkeypatch.setattr(agent_router_module, "_build_sdk_runtime_dependencies", lambda: (object(), object()))
    monkeypatch.setattr(agent_router_module, "sdk_advanced_rag", fake_sdk_run)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post(
        "/api/agents/run",
        json={
            "query": "Run with additive controls",
            "controls": {
                "rerank": {"enabled": False},
                "query_expansion": {"enabled": True},
                "hitl": {"enabled": True},
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["sub_answers"] == []
    assert captured == {
        "query": "Run with additive controls",
        "config": {
            "rerank": {"enabled": False},
            "query_expansion": {"enabled": True},
            "hitl": {"enabled": True},
        },
    }


def test_post_run_defaults_hitl_control_off_until_explicitly_enabled(monkeypatch) -> None:
    from routers import agent as agent_router_module
    from schemas import RuntimeAgentRunResponse

    captured: dict[str, object] = {}

    def fake_sdk_run(query, *, vector_store, model, config=None):
        captured["query"] = query
        captured["config"] = config
        return RuntimeAgentRunResponse(
            main_question=query,
            thread_id="550e8400-e29b-41d4-a716-446655440011",
            sub_qa=[],
            sub_answers=[],
            output=f"Echo: {query}",
        )

    monkeypatch.setattr(agent_router_module, "_build_sdk_runtime_dependencies", lambda: (object(), object()))
    monkeypatch.setattr(agent_router_module, "sdk_advanced_rag", fake_sdk_run)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post(
        "/api/agents/run",
        json={
            "query": "Run with default-off hitl",
            "controls": {
                "hitl": {},
            },
        },
    )

    assert response.status_code == 200
    assert captured == {
        "query": "Run with default-off hitl",
        "config": {
            "hitl": {"enabled": False},
        },
    }


def test_post_run_async_forwards_same_normalized_controls_as_sync_run(monkeypatch) -> None:
    from routers import agent as agent_router_module
    from schemas import RuntimeAgentRunAsyncStartResponse

    captured: dict[str, object] = {}

    def fake_sdk_run_async(query, *, vector_store, model, config=None):
        captured["query"] = query
        captured["config"] = config
        return RuntimeAgentRunAsyncStartResponse(
            job_id="job-456",
            run_id="run-456",
            thread_id="550e8400-e29b-41d4-a716-446655440012",
            status="queued",
        )

    monkeypatch.setattr(agent_router_module, "_build_sdk_runtime_dependencies", lambda: (object(), object()))
    monkeypatch.setattr(agent_router_module, "sdk_run_async", fake_sdk_run_async)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post(
        "/api/agents/run-async",
        json={
            "query": "Queue with additive controls",
            "thread_id": "550e8400-e29b-41d4-a716-446655440012",
            "controls": {
                "rerank": {"enabled": False},
                "query_expansion": {"enabled": True},
                "hitl": {"enabled": False},
            },
        },
    )

    assert response.status_code == 200
    assert captured == {
        "query": "Queue with additive controls",
        "config": {
            "thread_id": "550e8400-e29b-41d4-a716-446655440012",
            "rerank": {"enabled": False},
            "query_expansion": {"enabled": True},
            "hitl": {"enabled": False},
        },
    }


def test_run_async_and_status_preserve_same_thread_id(monkeypatch) -> None:
    from routers import agent as agent_router_module
    from schemas import RuntimeAgentRunAsyncStartResponse, RuntimeAgentRunAsyncStatusResponse

    thread_id = "550e8400-e29b-41d4-a716-446655440002"

    monkeypatch.setattr(agent_router_module, "_build_sdk_runtime_dependencies", lambda: (object(), object()))
    monkeypatch.setattr(
        agent_router_module,
        "sdk_run_async",
        lambda *args, **kwargs: RuntimeAgentRunAsyncStartResponse(
            job_id="job-789",
            run_id="run-789",
            thread_id=thread_id,
            status="running",
        ),
    )
    monkeypatch.setattr(
        agent_router_module,
        "sdk_get_run_status",
        lambda _job_id: RuntimeAgentRunAsyncStatusResponse(
            job_id="job-789",
            run_id="run-789",
            thread_id=thread_id,
            status="running",
        ),
    )

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    start_response = client.post("/api/agents/run-async", json={"query": "Track continuity"})
    status_response = client.get("/api/agents/run-status/job-789")

    assert start_response.status_code == 200
    assert status_response.status_code == 200
    assert start_response.json()["thread_id"] == thread_id
    assert status_response.json()["thread_id"] == thread_id


def test_run_endpoints_reject_invalid_thread_id_format() -> None:
    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post("/api/agents/run", json={"query": "Bad thread", "thread_id": "not-a-uuid"})

    assert response.status_code == 422
    assert any("thread_id must be a valid UUID string." in detail["msg"] for detail in response.json()["detail"])


def test_get_run_status_returns_subquestions_before_final_completion(monkeypatch) -> None:
    from routers import agent as agent_router_module
    from schemas import AgentRunStageMetadata, RuntimeAgentRunAsyncStatusResponse, SubQuestionAnswer

    def fake_sdk_get_run_status(job_id):
        assert job_id == "job-123"
        return RuntimeAgentRunAsyncStatusResponse(
            job_id="job-123",
            run_id="run-123",
            thread_id="550e8400-e29b-41d4-a716-446655440000",
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
            sub_answers=[
                SubQuestionAnswer(
                    sub_question="First question?",
                    sub_answer="",
                )
            ],
            output="",
            result=None,
            error=None,
            cancel_requested=False,
            started_at=None,
            finished_at=None,
            elapsed_ms=None,
        )

    monkeypatch.setattr(agent_router_module, "sdk_get_run_status", fake_sdk_get_run_status)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.get("/api/agents/run-status/job-123")
    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-123",
        "run_id": "run-123",
        "thread_id": "550e8400-e29b-41d4-a716-446655440000",
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
        "sub_answers": [
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
        "started_at": None,
        "finished_at": None,
        "elapsed_ms": None,
    }


def test_get_run_status_returns_completed_shape_with_result_and_timing(monkeypatch) -> None:
    from routers import agent as agent_router_module
    from schemas import AgentRunStageMetadata, CitationSourceRow, RuntimeAgentRunAsyncStatusResponse, RuntimeAgentRunResponse, SubQuestionAnswer

    def fake_sdk_get_run_status(job_id):
        assert job_id == "job-456"
        return RuntimeAgentRunAsyncStatusResponse(
            job_id="job-456",
            run_id="run-456",
            thread_id="550e8400-e29b-41d4-a716-446655440001",
            status="completed",
            message="Run completed.",
            stage="completed",
            stages=[
                AgentRunStageMetadata(
                    stage="subquestions_ready",
                    status="completed",
                    sub_question="",
                    lane_index=0,
                    lane_total=1,
                    emitted_at=101.0,
                ),
                AgentRunStageMetadata(
                    stage="synthesize",
                    status="completed",
                    sub_question="What is NATO?",
                    lane_index=1,
                    lane_total=1,
                    emitted_at=101.4,
                ),
            ],
            decomposition_sub_questions=["What is NATO?"],
            sub_question_artifacts=[],
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="What is NATO?",
                    sub_answer="A political and military alliance.",
                    expanded_query="What is NATO and how is it structured?",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                )
            ],
            sub_answers=[
                SubQuestionAnswer(
                    sub_question="What is NATO?",
                    sub_answer="A political and military alliance.",
                    expanded_query="What is NATO and how is it structured?",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                )
            ],
            output="NATO is a political and military alliance. [1]",
            result=RuntimeAgentRunResponse(
                main_question="What is NATO?",
                thread_id="550e8400-e29b-41d4-a716-446655440001",
                sub_qa=[
                    SubQuestionAnswer(
                        sub_question="What is NATO?",
                        sub_answer="A political and military alliance.",
                        expanded_query="What is NATO and how is it structured?",
                        answerable=True,
                        verification_reason="grounded_in_reranked_documents",
                    )
                ],
                sub_answers=[
                    SubQuestionAnswer(
                        sub_question="What is NATO?",
                        sub_answer="A political and military alliance.",
                        expanded_query="What is NATO and how is it structured?",
                        answerable=True,
                        verification_reason="grounded_in_reranked_documents",
                    )
                ],
                output="NATO is a political and military alliance. [1]",
                final_citations=[
                    CitationSourceRow(
                        citation_index=1,
                        rank=1,
                        title="NATO overview",
                        source="docs://nato-overview",
                        content="NATO is a political and military alliance.",
                        document_id="doc-nato-overview",
                        score=0.96,
                    )
                ],
            ),
            error=None,
            cancel_requested=False,
            started_at=100.0,
            finished_at=101.5,
            elapsed_ms=1500,
        )

    monkeypatch.setattr(agent_router_module, "sdk_get_run_status", fake_sdk_get_run_status)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.get("/api/agents/run-status/job-456")
    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-456",
        "run_id": "run-456",
        "thread_id": "550e8400-e29b-41d4-a716-446655440001",
        "status": "completed",
        "message": "Run completed.",
        "stage": "completed",
        "stages": [
            {
                "stage": "subquestions_ready",
                "status": "completed",
                "sub_question": "",
                "lane_index": 0,
                "lane_total": 1,
                "emitted_at": 101.0,
            },
            {
                "stage": "synthesize",
                "status": "completed",
                "sub_question": "What is NATO?",
                "lane_index": 1,
                "lane_total": 1,
                "emitted_at": 101.4,
            },
        ],
        "decomposition_sub_questions": ["What is NATO?"],
        "sub_question_artifacts": [],
        "sub_qa": [
            {
                "sub_question": "What is NATO?",
                "sub_answer": "A political and military alliance.",
                "tool_call_input": "",
                "expanded_query": "What is NATO and how is it structured?",
                "sub_agent_response": "",
                "answerable": True,
                "verification_reason": "grounded_in_reranked_documents",
            }
        ],
        "sub_answers": [
            {
                "sub_question": "What is NATO?",
                "sub_answer": "A political and military alliance.",
                "tool_call_input": "",
                "expanded_query": "What is NATO and how is it structured?",
                "sub_agent_response": "",
                "answerable": True,
                "verification_reason": "grounded_in_reranked_documents",
            }
        ],
        "output": "NATO is a political and military alliance. [1]",
        "result": {
            "main_question": "What is NATO?",
            "thread_id": "550e8400-e29b-41d4-a716-446655440001",
            "sub_qa": [
                {
                    "sub_question": "What is NATO?",
                    "sub_answer": "A political and military alliance.",
                    "tool_call_input": "",
                    "expanded_query": "What is NATO and how is it structured?",
                    "sub_agent_response": "",
                    "answerable": True,
                    "verification_reason": "grounded_in_reranked_documents",
                }
            ],
            "sub_answers": [
                {
                    "sub_question": "What is NATO?",
                    "sub_answer": "A political and military alliance.",
                    "tool_call_input": "",
                    "expanded_query": "What is NATO and how is it structured?",
                    "sub_agent_response": "",
                    "answerable": True,
                    "verification_reason": "grounded_in_reranked_documents",
                }
            ],
            "output": "NATO is a political and military alliance. [1]",
            "final_citations": [
                {
                    "citation_index": 1,
                    "rank": 1,
                    "title": "NATO overview",
                    "source": "docs://nato-overview",
                    "content": "NATO is a political and military alliance.",
                    "document_id": "doc-nato-overview",
                    "score": 0.96,
                }
            ],
        },
        "error": None,
        "cancel_requested": False,
        "started_at": 100.0,
        "finished_at": 101.5,
        "elapsed_ms": 1500,
    }


def test_post_run_cancel_returns_success(monkeypatch) -> None:
    from routers import agent as agent_router_module
    from schemas import RuntimeAgentRunAsyncCancelResponse

    monkeypatch.setattr(
        agent_router_module,
        "sdk_cancel_run",
        lambda _job_id: RuntimeAgentRunAsyncCancelResponse(status="success", message="Cancellation requested."),
    )

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post("/api/agents/run-cancel/job-123")
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "Cancellation requested."}


def test_get_run_status_not_found_maps_to_404(monkeypatch) -> None:
    from routers import agent as agent_router_module

    monkeypatch.setattr(
        agent_router_module,
        "sdk_get_run_status",
        lambda _job_id: (_ for _ in ()).throw(SDKConfigurationError("Job not found.")),
    )

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.get("/api/agents/run-status/missing-job")
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found."}


def test_post_run_cancel_not_found_maps_to_404(monkeypatch) -> None:
    from routers import agent as agent_router_module

    monkeypatch.setattr(
        agent_router_module,
        "sdk_cancel_run",
        lambda _job_id: (_ for _ in ()).throw(SDKConfigurationError("Job not found or already finished.")),
    )

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post("/api/agents/run-cancel/missing-job")
    assert response.status_code == 404
    assert response.json() == {"detail": "Job not found or already finished."}


def test_post_run_resume_returns_status_with_stable_thread_id(monkeypatch) -> None:
    from routers import agent as agent_router_module
    from schemas import RuntimeAgentRunAsyncStatusResponse, RuntimeAgentRunResponse

    thread_id = "550e8400-e29b-41d4-a716-446655440003"
    captured: dict[str, object] = {}

    def fake_sdk_resume_run(job_id: str, *, resume):
        captured["job_id"] = job_id
        captured["resume"] = resume
        return RuntimeAgentRunAsyncStatusResponse(
            job_id=job_id,
            run_id="run-003",
            thread_id=thread_id,
            status="success",
            message="Completed.",
            stage="completed",
            result=RuntimeAgentRunResponse(
                main_question="Approve run?",
                thread_id=thread_id,
                sub_qa=[],
                sub_answers=[],
                output="Recovered successfully.",
            ),
        )

    monkeypatch.setattr(agent_router_module, "sdk_resume_run", fake_sdk_resume_run)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post("/api/agents/run-resume/job-003", json={"resume": {"approved": True}})

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-003"
    assert response.json()["thread_id"] == thread_id
    assert response.json()["result"]["thread_id"] == thread_id
    assert response.json()["result"]["output"] == "Recovered successfully."
    assert captured == {"job_id": "job-003", "resume": {"approved": True}}


@pytest.mark.parametrize(
    ("detail", "expected_status"),
    [
        ("Run cannot be resumed from status 'running'.", 409),
        ("Run cannot be resumed from status 'success'.", 409),
        ("Run cannot be resumed from status 'cancelled'.", 409),
        ("Job not found.", 404),
    ],
)
def test_post_run_resume_maps_valid_and_invalid_transition_errors(
    monkeypatch, detail: str, expected_status: int
) -> None:
    from routers import agent as agent_router_module

    monkeypatch.setattr(
        agent_router_module,
        "sdk_resume_run",
        lambda _job_id, *, resume: (_ for _ in ()).throw(SDKConfigurationError(detail)),
    )

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post("/api/agents/run-resume/job-transition", json={"resume": {"approved": True}})

    assert response.status_code == expected_status
    assert response.json() == {"detail": detail}
