from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from agent_search.runtime import runner as runtime_runner
from agent_search.runtime.graph.state import RuntimeGraphContext
from agent_search.runtime.lifecycle_events import RuntimeLifecycleEvent
from schemas import RuntimeAgentRunRequest, SubQuestionAnswer
from services import agent_service


class _CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


def test_sdk_sync_run_e2e_uses_runtime_runner_with_caller_dependencies(monkeypatch) -> None:
    sentinel_model = object()
    sentinel_vector_store = _CompatibleVectorStore()
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        runtime_runner,
        "execute_runtime_graph",
        lambda *, context, run_metadata, config=None, lifecycle_callback=None: captured.update(
            {
                "payload_query": context.payload.query,
                "run_vector_store": context.vector_store,
                "run_model": context.model,
                "initial_search_context": context.initial_search_context,
                "run_metadata": run_metadata,
                "config": config,
                "lifecycle_callback": lifecycle_callback,
            }
        )
        or agent_service.build_agent_graph_state(
            main_question=context.payload.query,
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

    response = public_api.advanced_rag(
        "How does SDK sync wiring work?",
        model=sentinel_model,
        vector_store=sentinel_vector_store,
    )

    assert response.main_question == "How does SDK sync wiring work?"
    assert response.output == "Final answer with citation [1]."
    assert captured == {
        "payload_query": "How does SDK sync wiring work?",
        "run_vector_store": sentinel_vector_store,
        "run_model": sentinel_model,
        "initial_search_context": [],
        "run_metadata": captured["run_metadata"],
        "config": {
            "configurable": {
                "thread_id": captured["run_metadata"].thread_id,
                "checkpoint_id": captured["run_metadata"].thread_id,
            }
        },
        "lifecycle_callback": None,
    }


def test_runtime_runner_forwards_lifecycle_callback_and_maps_response(monkeypatch) -> None:
    emitted_events: list[RuntimeLifecycleEvent] = []

    monkeypatch.setattr(
        runtime_runner,
        "execute_runtime_graph",
        lambda *, context, run_metadata, config=None, lifecycle_callback=None: lifecycle_callback(
            RuntimeLifecycleEvent(
                event_type="run.completed",
                event_id=f"{run_metadata.run_id}:000001",
                run_id=run_metadata.run_id,
                thread_id=run_metadata.thread_id,
                trace_id=run_metadata.trace_id,
                stage="synthesize_final",
                status="success",
                emitted_at="2026-03-12T23:30:00+00:00",
            )
        )
        or {
            "main_question": context.payload.query,
            "decomposition_sub_questions": [],
            "sub_question_artifacts": [],
            "final_answer": "final answer",
            "citation_rows_by_index": {},
            "run_metadata": run_metadata,
            "sub_qa": [],
            "output": "final answer",
            "stage_snapshots": [],
        },
    )

    response = runtime_runner.run_runtime_agent(
        RuntimeAgentRunRequest(query="How do lifecycle callbacks work?"),
        model=object(),
        vector_store=_CompatibleVectorStore(),
        lifecycle_callback=emitted_events.append,
    )

    assert response.main_question == "How do lifecycle callbacks work?"
    assert response.output == "final answer"
    assert [event.event_type for event in emitted_events] == ["run.completed"]
    assert isinstance(emitted_events[0], RuntimeLifecycleEvent)
