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


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


def test_advanced_rag_signature_requires_query_vector_store_and_model() -> None:
    signature = inspect.signature(public_api.advanced_rag)
    assert (
        str(signature)
        == "(query: 'str', *, vector_store: 'Any', model: 'Any', config: 'dict[str, Any] | None' = None, callbacks: 'list[Any] | None' = None, langfuse_callback: 'Any | None' = None) -> 'RuntimeAgentRunResponse'"
    )
    assert signature.parameters["query"].default is inspect._empty
    assert signature.parameters["vector_store"].default is inspect._empty
    assert signature.parameters["model"].default is inspect._empty


def test_advanced_rag_returns_runtime_response_model(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_runtime_agent(payload, model, vector_store, callbacks=None, langfuse_callback=None):
        captured["query"] = payload.query
        captured["model"] = model
        captured["vector_store"] = vector_store
        captured["callbacks"] = callbacks
        captured["langfuse_callback"] = langfuse_callback
        return RuntimeAgentRunResponse(main_question=payload.query, sub_qa=[], output="ok")

    monkeypatch.setattr(public_api, "run_runtime_agent", fake_run_runtime_agent)
    monkeypatch.setattr(public_api, "build_langfuse_callback_handler", lambda **_kwargs: None)

    sentinel_model = object()
    sentinel_vector_store = _CompatibleVectorStore()
    callback_marker = object()
    response = public_api.advanced_rag(
        "sdk contract query",
        model=sentinel_model,
        vector_store=sentinel_vector_store,
        callbacks=[callback_marker],
    )

    assert isinstance(response, RuntimeAgentRunResponse)
    assert response.main_question == "sdk contract query"
    assert response.output == "ok"
    assert captured == {
        "query": "sdk contract query",
        "model": sentinel_model,
        "vector_store": sentinel_vector_store,
        "callbacks": [callback_marker],
        "langfuse_callback": None,
    }


def test_advanced_rag_raises_configuration_error_when_model_is_none() -> None:
    try:
        public_api.advanced_rag("q", model=None, vector_store=_CompatibleVectorStore())
    except SDKConfigurationError as exc:
        assert str(exc) == "model is required and cannot be None"
    else:
        raise AssertionError("Expected SDKConfigurationError for missing model")


def test_advanced_rag_passes_explicit_langfuse_callback(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_runtime_agent(payload, model, vector_store, callbacks=None, langfuse_callback=None):
        captured["query"] = payload.query
        captured["callbacks"] = callbacks
        captured["langfuse_callback"] = langfuse_callback
        return RuntimeAgentRunResponse(main_question=payload.query, sub_qa=[], output="ok")

    monkeypatch.setattr(public_api, "run_runtime_agent", fake_run_runtime_agent)

    explicit_callback = object()
    response = public_api.advanced_rag(
        "sdk callback query",
        model=object(),
        vector_store=_CompatibleVectorStore(),
        langfuse_callback=explicit_callback,
    )

    assert response.output == "ok"
    assert captured["langfuse_callback"] is explicit_callback
    assert explicit_callback in (captured["callbacks"] or [])
