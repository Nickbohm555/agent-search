from __future__ import annotations

import inspect
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from agent_search.errors import SDKConfigurationError
from schemas import RuntimeAgentRunResponse


def test_run_sync_signature_requires_query_vector_store_and_model() -> None:
    signature = inspect.signature(public_api.run)
    assert str(signature) == "(query: 'str', *, vector_store: 'Any', model: 'Any', config: 'dict[str, Any] | None' = None) -> 'RuntimeAgentRunResponse'"
    assert signature.parameters["query"].default is inspect._empty
    assert signature.parameters["vector_store"].default is inspect._empty
    assert signature.parameters["model"].default is inspect._empty


def test_run_sync_returns_runtime_response_model(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_runtime_agent(payload, db, model, vector_store):
        captured["query"] = payload.query
        captured["db"] = db
        captured["model"] = model
        captured["vector_store"] = vector_store
        return RuntimeAgentRunResponse(main_question=payload.query, sub_qa=[], output="ok")

    monkeypatch.setattr(public_api, "run_runtime_agent", fake_run_runtime_agent)

    sentinel_model = object()
    sentinel_vector_store = object()
    response = public_api.run(
        "sdk contract query",
        model=sentinel_model,
        vector_store=sentinel_vector_store,
    )

    assert isinstance(response, RuntimeAgentRunResponse)
    assert response.main_question == "sdk contract query"
    assert response.output == "ok"
    assert captured == {
        "query": "sdk contract query",
        "db": None,
        "model": sentinel_model,
        "vector_store": sentinel_vector_store,
    }


def test_run_sync_raises_configuration_error_when_model_is_none() -> None:
    try:
        public_api.run("q", model=None, vector_store=object())
    except SDKConfigurationError as exc:
        assert str(exc) == "model is required and cannot be None"
    else:
        raise AssertionError("Expected SDKConfigurationError for missing model")
