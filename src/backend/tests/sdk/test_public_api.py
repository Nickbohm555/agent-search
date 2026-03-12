from __future__ import annotations

import inspect
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from agent_search.errors import SDKConfigurationError
from agent_search.runtime import runner as runtime_runner
from schemas import CitationSourceRow, RuntimeAgentRunResponse, SubQuestionAnswer
from services import agent_service


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


def test_advanced_rag_signature_requires_query_vector_store_and_model() -> None:
    signature = inspect.signature(public_api.advanced_rag)
    assert (
        str(signature)
        == "(query: 'str', *, vector_store: 'Any', model: 'Any', config: 'dict[str, Any] | None' = None, callbacks: 'list[Any] | None' = None, langfuse_callback: 'Any | None' = None, langfuse_settings: 'Mapping[str, Any] | None' = None) -> 'RuntimeAgentRunResponse'"
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
        return RuntimeAgentRunResponse(
            main_question=payload.query,
            thread_id="550e8400-e29b-41d4-a716-446655440020",
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="Which lane completed?",
                    sub_answer="The synthesis lane completed with grounded evidence.",
                    tool_call_input='{"query":"Which lane completed?"}',
                    expanded_query="Which orchestration lane completed under LangGraph?",
                    sub_agent_response="The lane completed after retrieval and synthesis.",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                )
            ],
            output="ok [2]",
            final_citations=[
                CitationSourceRow(
                    citation_index=2,
                    rank=1,
                    title="Lifecycle evidence",
                    source="docs://lifecycle",
                    content="Synthesis completed after retrieval and answer stages.",
                    document_id="doc-2",
                    score=0.91,
                )
            ],
        )

    monkeypatch.setattr(public_api, "run_runtime_agent", fake_run_runtime_agent)
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
    assert response.thread_id == "550e8400-e29b-41d4-a716-446655440020"
    assert response.output == "ok [2]"
    assert response.sub_qa[0].answerable is True
    assert response.sub_qa[0].verification_reason == "grounded_in_reranked_documents"
    assert response.final_citations[0].citation_index == 2
    assert response.final_citations[0].title == "Lifecycle evidence"
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


def test_build_langfuse_callback_delegates_to_tracing_utility(monkeypatch) -> None:
    marker = object()
    captured: dict[str, object] = {}

    def fake_builder(*, scope: str, sampling_key: str | None = None, settings=None):
        captured["scope"] = scope
        captured["sampling_key"] = sampling_key
        captured["settings"] = settings
        return marker

    monkeypatch.setattr(public_api, "_build_langfuse_callback_handler", fake_builder)
    callback = public_api.build_langfuse_callback(sampling_key="sdk-test")

    assert callback is marker
    assert captured["scope"] == "runtime"
    assert captured["sampling_key"] == "sdk-test"
    assert captured["settings"] is not None


def test_advanced_rag_does_not_build_langfuse_callback_from_settings(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_build_langfuse_callback(*, sampling_key=None, settings=None):
        _ = sampling_key, settings
        raise AssertionError("build_langfuse_callback should not be called by advanced_rag")

    def fake_run_runtime_agent(payload, model, vector_store, callbacks=None, langfuse_callback=None):
        captured["callbacks"] = callbacks
        captured["langfuse_callback"] = langfuse_callback
        return RuntimeAgentRunResponse(main_question=payload.query, sub_qa=[], output="ok")

    monkeypatch.setattr(public_api, "build_langfuse_callback", fake_build_langfuse_callback)
    monkeypatch.setattr(public_api, "run_runtime_agent", fake_run_runtime_agent)

    response = public_api.advanced_rag(
        "query for settings",
        model=object(),
        vector_store=_CompatibleVectorStore(),
        langfuse_settings={
            "enabled": True,
            "public_key": "pk",
            "secret_key": "sk",
        },
    )

    assert response.output == "ok"
    assert captured["langfuse_callback"] is None
    assert captured["callbacks"] is None


def test_advanced_rag_cutover_blocks_legacy_orchestration(monkeypatch) -> None:
    sentinel_model = object()
    sentinel_vector_store = _CompatibleVectorStore()
    captured: dict[str, object] = {}

    def fake_execute_runtime_graph(*, context, run_metadata, config=None):
        captured["query"] = context.payload.query
        captured["vector_store"] = context.vector_store
        captured["model"] = context.model
        captured["config"] = config
        return agent_service.build_agent_graph_state(
            main_question=context.payload.query,
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="Which runtime completed the request?",
                    sub_answer="The LangGraph runtime path completed the request.",
                )
            ],
            final_answer="The LangGraph runtime path completed the request.",
            run_metadata=run_metadata,
        )

    monkeypatch.setattr(runtime_runner, "execute_runtime_graph", fake_execute_runtime_graph)
    monkeypatch.setattr(
        runtime_runner.legacy_service,
        "run_parallel_graph_runner",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("legacy orchestration should not execute")),
    )

    response = public_api.advanced_rag(
        "Which runtime completed the request?",
        model=sentinel_model,
        vector_store=sentinel_vector_store,
    )

    assert response.output == "The LangGraph runtime path completed the request."
    assert response.sub_qa[0].sub_answer == "The LangGraph runtime path completed the request."
    assert captured == {
        "query": "Which runtime completed the request?",
        "vector_store": sentinel_vector_store,
        "model": sentinel_model,
        "config": None,
    }
