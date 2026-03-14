from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.errors import SDKConfigurationError
from routers.agent import router as agent_router
from schemas import (
    AgentRunStageMetadata,
    RuntimeAgentRunAsyncStartResponse,
    RuntimeAgentRunAsyncStatusResponse,
    RuntimeAgentRunRequest,
    RuntimeAgentRunResponse,
)


def test_runtime_agent_run_request_accepts_custom_prompts_alias_and_ignores_unknown_keys() -> None:
    payload = RuntimeAgentRunRequest.model_validate(
        {
            "query": "Use a custom prompt",
            "custom-prompts": {
                "subanswer": "Ground each subanswer in retrieved evidence.",
                "synthesis": "Write a concise synthesis with citations.",
                "ignored": "ignore this",
            },
        }
    )

    assert payload.custom_prompts is not None
    assert payload.custom_prompts.subanswer == "Ground each subanswer in retrieved evidence."
    assert payload.custom_prompts.synthesis == "Write a concise synthesis with citations."
    assert payload.model_dump(exclude_none=True)["custom_prompts"] == {
        "subanswer": "Ground each subanswer in retrieved evidence.",
        "synthesis": "Write a concise synthesis with citations.",
    }


def test_post_run_returns_response_shape_from_runtime_agent(monkeypatch) -> None:
    from routers import agent as agent_router_module

    captured: dict[str, object] = {}
    sentinel_vector_store = object()
    sentinel_model = object()

    def fake_sdk_run(query, *, vector_store, model, config=None, checkpoint_db_url=None):
        captured["query"] = query
        captured["vector_store"] = vector_store
        captured["model"] = model
        captured["config"] = config
        captured["checkpoint_db_url"] = checkpoint_db_url
        return RuntimeAgentRunResponse(
            main_question=query,
            sub_items=[("What changed in policy X?", "Policy X was revised in January 2026.")],
            output=f"Echo: {query}",
        )

    monkeypatch.setattr(agent_router_module, "_build_sdk_runtime_dependencies", lambda: (sentinel_vector_store, sentinel_model))
    monkeypatch.setattr(agent_router_module, "sdk_advanced_rag", fake_sdk_run)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post(
        "/api/agents/run",
        json={
            "query": "Find Hormuz risks",
            "checkpoint_db_url": "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search",
            "controls": {"query_expansion": {"enabled": True}},
            "runtime_config": {"rerank": {"enabled": False}},
            "custom-prompts": {"subanswer": "Ground each answer."},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "main_question": "Find Hormuz risks",
        "thread_id": None,
        "sub_items": [["What changed in policy X?", "Policy X was revised in January 2026."]],
        "output": "Echo: Find Hormuz risks",
        "final_citations": [],
    }
    assert captured == {
        "query": "Find Hormuz risks",
        "vector_store": sentinel_vector_store,
        "model": sentinel_model,
        "checkpoint_db_url": "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search",
        "config": {
            "custom_prompts": {"subanswer": "Ground each answer."},
            "runtime_config": {"rerank": {"enabled": False}},
            "query_expansion": {"enabled": True},
        },
    }


def test_post_run_async_returns_start_response(monkeypatch) -> None:
    from routers import agent as agent_router_module

    captured: dict[str, object] = {}

    def fake_run_async(query, *, vector_store, model, config=None, checkpoint_db_url=None):
        captured["query"] = query
        captured["vector_store"] = vector_store
        captured["model"] = model
        captured["config"] = config
        captured["checkpoint_db_url"] = checkpoint_db_url
        return RuntimeAgentRunAsyncStartResponse(
            job_id="job-123",
            run_id="run-123",
            status="running",
        )

    monkeypatch.setattr(agent_router_module, "_build_sdk_runtime_dependencies", lambda: (object(), object()))
    monkeypatch.setattr(agent_router_module, "sdk_run_async", fake_run_async)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post(
        "/api/agents/run-async",
        json={
            "query": "Show me async flow",
            "checkpoint_db_url": "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search",
            "controls": {"hitl": {"subquestions": {"enabled": True}}},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-123",
        "run_id": "run-123",
        "thread_id": "",
        "status": "running",
    }
    assert captured["query"] == "Show me async flow"
    assert captured["config"] == {"hitl": {"enabled": True, "subquestions": {"enabled": True}}}
    assert captured["checkpoint_db_url"] == "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search"


def test_post_run_async_uses_app_database_url_for_hitl_when_checkpoint_db_url_omitted(monkeypatch) -> None:
    from routers import agent as agent_router_module

    captured: dict[str, object] = {}

    def fake_run_async(query, *, vector_store, model, config=None, checkpoint_db_url=None):
        captured["query"] = query
        captured["config"] = config
        captured["checkpoint_db_url"] = checkpoint_db_url
        return RuntimeAgentRunAsyncStartResponse(
            job_id="job-hitl-default",
            run_id="run-hitl-default",
            status="running",
        )

    monkeypatch.setattr(agent_router_module, "_build_sdk_runtime_dependencies", lambda: (object(), object()))
    monkeypatch.setattr(agent_router_module, "sdk_run_async", fake_run_async)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post(
        "/api/agents/run-async",
        json={
            "query": "Use app checkpoint default",
            "controls": {"hitl": {"subquestions": {"enabled": True}}},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-hitl-default",
        "run_id": "run-hitl-default",
        "thread_id": "",
        "status": "running",
    }
    assert captured["query"] == "Use app checkpoint default"
    assert captured["config"] == {"hitl": {"enabled": True, "subquestions": {"enabled": True}}}
    assert captured["checkpoint_db_url"] == agent_router_module.DATABASE_URL


def test_status_and_resume_routes_map_sdk_configuration_errors(monkeypatch) -> None:
    from routers import agent as agent_router_module

    monkeypatch.setattr(
        agent_router_module,
        "sdk_get_run_status",
        lambda _job_id: (_ for _ in ()).throw(SDKConfigurationError("Job not found.")),
    )
    monkeypatch.setattr(
        agent_router_module,
        "sdk_resume_run",
        lambda _job_id, resume: (_ for _ in ()).throw(SDKConfigurationError("Run is not resumable.")),
    )

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    status_response = client.get("/api/agents/run-status/job-missing")
    resume_response = client.post("/api/agents/run-resume/job-123", json={"resume": True})

    assert status_response.status_code == 404
    assert status_response.json() == {"detail": "Job not found."}
    assert resume_response.status_code == 409
    assert resume_response.json() == {"detail": "Run is not resumable."}


def test_resume_route_normalizes_typed_resume_payload_to_plain_dict(monkeypatch) -> None:
    from routers import agent as agent_router_module

    captured: dict[str, object] = {}

    def fake_resume(job_id, *, resume):
        captured["job_id"] = job_id
        captured["resume"] = resume
        return RuntimeAgentRunAsyncStatusResponse(
            job_id=job_id,
            run_id="run-typed-resume",
            thread_id="550e8400-e29b-41d4-a716-446655440099",
            status="running",
            message="Resume accepted.",
            stage="subquestions_ready",
            checkpoint_id="checkpoint-typed",
        )

    monkeypatch.setattr(agent_router_module, "sdk_resume_run", fake_resume)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post(
        "/api/agents/run-resume/job-typed",
        json={
            "resume": {
                "checkpoint_id": "checkpoint-typed",
                "decisions": [
                    {"subquestion_id": "sq-1", "action": "skip"},
                ],
            }
        },
    )

    assert response.status_code == 200
    assert captured == {
        "job_id": "job-typed",
        "resume": {
            "checkpoint_id": "checkpoint-typed",
            "decisions": [
                {"subquestion_id": "sq-1", "action": "skip"},
            ],
        },
    }


def test_status_route_returns_async_status_shape(monkeypatch) -> None:
    from routers import agent as agent_router_module

    monkeypatch.setattr(
        agent_router_module,
        "sdk_get_run_status",
        lambda _job_id: RuntimeAgentRunAsyncStatusResponse(
            job_id="job-123",
            run_id="run-123",
            thread_id="550e8400-e29b-41d4-a716-446655440017",
            status="success",
            stage="synthesize_final",
            output="done",
            result=RuntimeAgentRunResponse(
                main_question="done",
                thread_id="550e8400-e29b-41d4-a716-446655440017",
                sub_items=[],
                output="done",
            ),
        ),
    )

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.get("/api/agents/run-status/job-123")

    assert response.status_code == 200
    assert response.json()["job_id"] == "job-123"
    assert response.json()["run_id"] == "run-123"
    assert response.json()["thread_id"] == "550e8400-e29b-41d4-a716-446655440017"
    assert response.json()["status"] == "success"
    assert response.json()["result"]["main_question"] == "done"


def test_status_route_restores_missing_job_from_persisted_runtime_row(monkeypatch) -> None:
    from routers import agent as agent_router_module

    captured: dict[str, object] = {}

    def fake_restore(job_id: str, *, model=None, vector_store=None):
        captured["job_id"] = job_id
        captured["model"] = model
        captured["vector_store"] = vector_store
        return object()

    monkeypatch.setattr(agent_router_module, "restore_agent_run_job", fake_restore)
    monkeypatch.setattr(
        agent_router_module,
        "sdk_get_run_status",
        lambda job_id: RuntimeAgentRunAsyncStatusResponse(
            job_id=job_id,
            run_id=job_id,
            thread_id="550e8400-e29b-41d4-a716-446655440088",
            status="paused",
            message="Paused and awaiting resume input.",
            stage="subquestions_ready",
            stages=[AgentRunStageMetadata(stage="subquestions_ready", status="paused")],
            checkpoint_id="checkpoint-restore",
        ),
    )

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.get("/api/agents/run-status/job-restored")

    assert response.status_code == 200
    assert response.json()["status"] == "paused"
    assert response.json()["checkpoint_id"] == "checkpoint-restore"
    assert captured == {"job_id": "job-restored", "model": None, "vector_store": None}


def test_resume_route_restores_missing_job_with_runtime_dependencies_before_dispatch(monkeypatch) -> None:
    from routers import agent as agent_router_module

    captured: dict[str, object] = {}
    sentinel_vector_store = object()
    sentinel_model = object()

    monkeypatch.setattr(agent_router_module, "get_agent_run_job", lambda _job_id: None)
    monkeypatch.setattr(agent_router_module, "_build_sdk_runtime_dependencies", lambda: (sentinel_vector_store, sentinel_model))

    def fake_restore(job_id: str, *, model=None, vector_store=None):
        captured["job_id"] = job_id
        captured["model"] = model
        captured["vector_store"] = vector_store
        return object()

    monkeypatch.setattr(agent_router_module, "restore_agent_run_job", fake_restore)
    monkeypatch.setattr(
        agent_router_module,
        "sdk_resume_run",
        lambda job_id, resume: RuntimeAgentRunAsyncStatusResponse(
            job_id=job_id,
            run_id=job_id,
            thread_id="550e8400-e29b-41d4-a716-446655440099",
            status="running",
            message="Resuming from checkpoint.",
            stage="resuming",
            checkpoint_id="checkpoint-restore",
        ),
    )

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post("/api/agents/run-resume/job-restored", json={"resume": True})

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert captured == {"job_id": "job-restored", "model": sentinel_model, "vector_store": sentinel_vector_store}
