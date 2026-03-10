from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from agent_search.runtime import runner as runtime_runner
from schemas import RuntimeAgentRunRequest, RuntimeAgentRunResponse, SubQuestionAnswer
from services import agent_service


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


def test_sdk_sync_run_e2e_uses_runtime_runner_with_caller_dependencies(monkeypatch) -> None:
    sentinel_model = object()
    sentinel_vector_store = _CompatibleVectorStore()
    captured: dict[str, object] = {}

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

    response = public_api.advanced_rag(
        "How does SDK sync wiring work?",
        model=sentinel_model,
        vector_store=sentinel_vector_store,
    )

    assert response.main_question == "How does SDK sync wiring work?"
    assert response.output == "Final answer with citation [1]."
    assert response.sub_qa[0].sub_question == "What is the key fact?"
    assert response.sub_qa[0].sub_answer == "The key fact is captured with citation [1]."
    assert captured == {
        "payload_query": "How does SDK sync wiring work?",
        "run_vector_store": sentinel_vector_store,
        "run_model": sentinel_model,
        "initial_search_context": [],
    }


def test_runtime_runner_emits_langfuse_stage_hooks(monkeypatch) -> None:
    captured: dict[str, list[dict[str, object]]] = {"traces": [], "spans": [], "scores": [], "ends": []}

    monkeypatch.setattr(
        runtime_runner,
        "start_langfuse_trace",
        lambda **kwargs: captured["traces"].append(kwargs) or object(),
    )
    monkeypatch.setattr(
        runtime_runner,
        "start_langfuse_span",
        lambda **kwargs: captured["spans"].append(kwargs) or object(),
    )
    monkeypatch.setattr(
        runtime_runner,
        "record_langfuse_score",
        lambda **kwargs: captured["scores"].append(kwargs),
    )
    monkeypatch.setattr(
        runtime_runner,
        "end_langfuse_observation",
        lambda observation, **kwargs: captured["ends"].append(kwargs),
    )

    monkeypatch.setattr(
        agent_service,
        "run_parallel_graph_runner",
        lambda **kwargs: agent_service.build_agent_graph_state(
            main_question=kwargs["payload"].query,
            sub_qa=[],
            final_answer="final answer",
            run_metadata=kwargs["run_metadata"],
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

    runtime_runner.run_runtime_agent(
        RuntimeAgentRunRequest(query="How do traces work?"),
        model=object(),
        vector_store=_CompatibleVectorStore(),
        langfuse_callback=object(),
    )

    assert captured["traces"]
    assert any(item["name"] == "runtime.agent_run" for item in captured["traces"])
    assert captured["scores"]
    assert captured["ends"]


def test_runtime_runner_skips_langfuse_stage_hooks_without_callback(monkeypatch) -> None:
    captured: dict[str, list[dict[str, object]]] = {"traces": [], "spans": [], "scores": [], "ends": []}

    monkeypatch.setattr(
        runtime_runner,
        "start_langfuse_trace",
        lambda **kwargs: captured["traces"].append(kwargs) or object(),
    )
    monkeypatch.setattr(
        runtime_runner,
        "start_langfuse_span",
        lambda **kwargs: captured["spans"].append(kwargs) or object(),
    )
    monkeypatch.setattr(
        runtime_runner,
        "record_langfuse_score",
        lambda **kwargs: captured["scores"].append(kwargs),
    )
    monkeypatch.setattr(
        runtime_runner,
        "end_langfuse_observation",
        lambda observation, **kwargs: captured["ends"].append(kwargs),
    )

    monkeypatch.setattr(
        agent_service,
        "run_parallel_graph_runner",
        lambda **kwargs: agent_service.build_agent_graph_state(
            main_question=kwargs["payload"].query,
            sub_qa=[],
            final_answer="final answer",
            run_metadata=kwargs["run_metadata"],
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

    runtime_runner.run_runtime_agent(
        RuntimeAgentRunRequest(query="No callback tracing"),
        model=object(),
        vector_store=_CompatibleVectorStore(),
    )

    assert captured == {"traces": [], "spans": [], "scores": [], "ends": []}
