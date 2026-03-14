from __future__ import annotations

import inspect
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from agent_search.errors import SDKConfigurationError
from schemas import CitationSourceRow, RuntimeAgentRunResponse, SubQuestionAnswer


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


def test_advanced_rag_signature_matches_clean_public_contract() -> None:
    signature = inspect.signature(public_api.advanced_rag)
    assert (
        str(signature)
        == "(query: 'str', *, vector_store: 'Any', model: 'Any', config: 'dict[str, Any] | None' = None, callbacks: 'list[Any] | None' = None) -> 'RuntimeAgentRunResponse'"
    )
    assert signature.parameters["query"].default is inspect._empty
    assert signature.parameters["vector_store"].default is inspect._empty
    assert signature.parameters["model"].default is inspect._empty


def test_advanced_rag_returns_runtime_response_model(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_runtime_agent(payload, model, vector_store, callbacks=None):
        captured["payload"] = payload.model_dump(mode="json", exclude_none=True)
        captured["model"] = model
        captured["vector_store"] = vector_store
        captured["callbacks"] = callbacks
        return RuntimeAgentRunResponse(
            main_question=payload.query,
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
    assert response.output == "ok [2]"
    assert response.sub_answers == response.sub_qa
    assert response.final_citations[0].citation_index == 2
    assert captured == {
        "payload": {"query": "sdk contract query"},
        "model": sentinel_model,
        "vector_store": sentinel_vector_store,
        "callbacks": [callback_marker],
    }


def test_advanced_rag_builds_clean_runtime_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_runtime_agent(payload, model, vector_store, callbacks=None):
        _ = model, vector_store, callbacks
        captured["payload"] = payload.model_dump(mode="json", exclude_none=True)
        return RuntimeAgentRunResponse(main_question=payload.query, sub_qa=[], output="ok")

    monkeypatch.setattr(public_api, "run_runtime_agent", fake_run_runtime_agent)

    response = public_api.advanced_rag(
        "sdk runtime config query",
        model=object(),
        vector_store=_CompatibleVectorStore(),
        config={
            "rerank": {"enabled": False},
            "query_expansion": {"enabled": True},
            "hitl": {"subquestions": {"enabled": True}},
            "runtime_config": {
                "rerank": {"enabled": False},
                "query_expansion": {"enabled": True},
                "custom_prompts": {"subanswer": "per-run subanswer prompt"},
            },
            "custom_prompts": {
                "subanswer": "default subanswer prompt",
                "synthesis": "default synthesis prompt",
            },
        },
    )

    assert response.output == "ok"
    assert captured["payload"] == {
        "query": "sdk runtime config query",
        "controls": {
            "rerank": {"enabled": False},
            "query_expansion": {"enabled": True},
            "hitl": {"enabled": True, "subquestions": {"enabled": True}},
        },
        "runtime_config": {
            "rerank": {"enabled": False},
            "query_expansion": {"enabled": True},
        },
        "custom_prompts": {
            "subanswer": "per-run subanswer prompt",
            "synthesis": "default synthesis prompt",
        },
    }


def test_advanced_rag_rejects_missing_runtime_dependencies() -> None:
    try:
        public_api.advanced_rag("missing model", model=None, vector_store=_CompatibleVectorStore())
        raise AssertionError("Expected SDKConfigurationError for missing model")
    except SDKConfigurationError as exc:
        assert str(exc) == "model is required and cannot be None"

    try:
        public_api.advanced_rag("missing vector store", model=object(), vector_store=None)
        raise AssertionError("Expected SDKConfigurationError for missing vector_store")
    except SDKConfigurationError as exc:
        assert str(exc) == "vector_store is required and cannot be None"
