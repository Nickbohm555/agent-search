from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from agent_search.runtime import runner as runtime_runner
from schemas import RuntimeAgentRunResponse, SubQuestionAnswer
from services import agent_service


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


def test_sdk_sync_run_e2e_uses_runtime_runner_with_caller_dependencies(monkeypatch) -> None:
    sentinel_model = object()
    sentinel_vector_store = _CompatibleVectorStore()
    captured: dict[str, object] = {}

    def fail_if_vector_store_lookup_called(*, connection, collection_name, embeddings):
        raise AssertionError(
            f"Expected provided vector_store to be used directly. "
            f"Unexpected lookup: connection={connection} collection={collection_name} embeddings={embeddings}"
        )

    monkeypatch.setattr(runtime_runner, "get_vector_store", fail_if_vector_store_lookup_called)
    monkeypatch.setattr(
        runtime_runner,
        "search_documents_for_context",
        lambda *, vector_store, query, k, score_threshold: captured.update(
            {
                "search_vector_store": vector_store,
                "search_query": query,
                "search_k": k,
                "search_score_threshold": score_threshold,
            }
        )
        or ["doc-1"],
    )
    monkeypatch.setattr(
        runtime_runner,
        "build_initial_search_context",
        lambda docs: [{"rank": 1, "title": "Doc One", "source": "test://doc-1"}],
    )
    monkeypatch.setattr(
        agent_service,
        "run_parallel_graph_runner",
        lambda *, payload, vector_store, model, run_metadata, initial_search_context: captured.update(
            {
                "payload_query": payload.query,
                "run_vector_store": vector_store,
                "run_model": model,
                "initial_search_context": initial_search_context,
            }
        )
        or agent_service.build_agent_graph_state(
            main_question=payload.query,
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="What is the key fact?",
                    sub_answer="The key fact is captured with citation [1].",
                )
            ],
            final_answer="Final answer with citation [1].",
            run_metadata=run_metadata,
        ),
    )
    monkeypatch.setattr(
        agent_service,
        "map_graph_state_to_runtime_response",
        lambda state: RuntimeAgentRunResponse(
            main_question=state.main_question,
            sub_qa=state.sub_qa,
            output=state.output,
        ),
    )

    response = public_api.run(
        "How does SDK sync wiring work?",
        model=sentinel_model,
        vector_store=sentinel_vector_store,
    )

    assert response.main_question == "How does SDK sync wiring work?"
    assert response.output == "Final answer with citation [1]."
    assert response.sub_qa[0].sub_question == "What is the key fact?"
    assert response.sub_qa[0].sub_answer == "The key fact is captured with citation [1]."
    assert captured == {
        "search_vector_store": sentinel_vector_store,
        "search_query": "How does SDK sync wiring work?",
        "search_k": agent_service._INITIAL_SEARCH_CONTEXT_K,
        "search_score_threshold": agent_service._INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD,
        "payload_query": "How does SDK sync wiring work?",
        "run_vector_store": sentinel_vector_store,
        "run_model": sentinel_model,
        "initial_search_context": [{"rank": 1, "title": "Doc One", "source": "test://doc-1"}],
    }
