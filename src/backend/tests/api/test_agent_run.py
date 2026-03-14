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
    RuntimeAgentRunAsyncStartResponse,
    RuntimeAgentRunAsyncStatusResponse,
    RuntimeAgentRunRequest,
    RuntimeAgentRunResponse,
    SubQuestionAnswer,
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

    def fake_sdk_run(query, *, vector_store, model, config=None):
        captured["query"] = query
        captured["vector_store"] = vector_store
        captured["model"] = model
        captured["config"] = config
        return RuntimeAgentRunResponse(
            main_question=query,
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
            "controls": {"query_expansion": {"enabled": True}},
            "runtime_config": {"rerank": {"enabled": False}},
            "custom-prompts": {"subanswer": "Ground each answer."},
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "main_question": "Find Hormuz risks",
        "thread_id": None,
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
        "config": {
            "custom_prompts": {"subanswer": "Ground each answer."},
            "runtime_config": {"rerank": {"enabled": False}},
            "query_expansion": {"enabled": True},
        },
    }


def test_post_run_async_returns_start_response(monkeypatch) -> None:
    from routers import agent as agent_router_module

    captured: dict[str, object] = {}

    def fake_run_async(query, *, vector_store, model, config=None):
        captured["query"] = query
        captured["vector_store"] = vector_store
        captured["model"] = model
        captured["config"] = config
        return RuntimeAgentRunAsyncStartResponse(
            job_id="job-123",
            run_id="run-123",
            thread_id="550e8400-e29b-41d4-a716-446655440016",
            status="running",
        )

    monkeypatch.setattr(agent_router_module, "_build_sdk_runtime_dependencies", lambda: (object(), object()))
    monkeypatch.setattr(agent_router_module, "sdk_run_async", fake_run_async)

    app = FastAPI()
    app.include_router(agent_router)
    client = TestClient(app)

    response = client.post(
        "/api/agents/run-async",
        json={"query": "Show me async flow", "controls": {"hitl": {"subquestions": {"enabled": True}}}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "job_id": "job-123",
        "run_id": "run-123",
        "thread_id": "550e8400-e29b-41d4-a716-446655440016",
        "status": "running",
    }
    assert captured["query"] == "Show me async flow"
    assert captured["config"] == {"hitl": {"enabled": True, "subquestions": {"enabled": True}}}


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
                sub_qa=[],
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
