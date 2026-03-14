from __future__ import annotations

from datetime import datetime, timezone
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime.graph.execution import execute_runtime_graph
from agent_search.runtime.graph.state import RuntimeGraphContext
from agent_search.runtime.lifecycle_events import LifecycleEventBuilder, RuntimeLifecycleEvent
from langgraph.graph import END, START, StateGraph
from schemas import GraphRunMetadata, RuntimeAgentRunRequest


def _run_metadata() -> GraphRunMetadata:
    return GraphRunMetadata(
        run_id="run-123",
        thread_id="550e8400-e29b-41d4-a716-446655440000",
        trace_id="trace-123",
        correlation_id="corr-123",
    )


def test_lifecycle_event_builder_emits_monotonic_ids_from_langgraph_signals() -> None:
    builder = LifecycleEventBuilder(
        run_metadata=_run_metadata(),
        clock=lambda: datetime(2026, 3, 12, 23, 30, 0, tzinfo=timezone.utc),
    )

    events = [
        builder.emit_run_started(),
        *builder.consume_stream_signal("tasks", {"name": "decompose", "input": {"query": "test"}}),
        *builder.consume_stream_signal("updates", {"decompose": {"decomposition_sub_questions": ["What changed?"]}}),
        *builder.consume_stream_signal("tasks", {"name": "decompose", "error": None, "result": {"ok": True}, "interrupts": []}),
        *builder.consume_stream_signal(
            "checkpoints",
            {
                "config": {"configurable": {"checkpoint_id": "cp-1"}},
                "metadata": {"source": "loop"},
                "next": ["search"],
            },
        ),
        builder.emit_terminal(status="success"),
    ]

    assert [event.event_type for event in events] == [
        "run.started",
        "stage.started",
        "stage.updated",
        "stage.completed",
        "checkpoint.created",
        "run.completed",
    ]
    assert [event.event_id for event in events] == [
        "run-123:000001",
        "run-123:000002",
        "run-123:000003",
        "run-123:000004",
        "run-123:000005",
        "run-123:000006",
    ]
    assert all(event.run_id == "run-123" for event in events)
    assert all(event.stage for event in events)


def test_lifecycle_event_builder_supports_recovery_retry_and_failure_transitions() -> None:
    builder = LifecycleEventBuilder(
        run_metadata=_run_metadata(),
        clock=lambda: datetime(2026, 3, 12, 23, 31, 0, tzinfo=timezone.utc),
    )

    events = [
        builder.emit_recovery_started(checkpoint_id="cp-2"),
        builder.emit_retrying(stage="search", error="transient backend failure"),
        builder.emit_terminal(status="error", error="transient backend failure"),
    ]

    assert [event.event_type for event in events] == [
        "run.recovered",
        "stage.retrying",
        "run.failed",
    ]
    assert events[0].status == "running"
    assert events[1].stage == "search"
    assert events[1].status == "retrying"
    assert events[2].status == "error"
    assert events[2].error == "transient backend failure"


def test_execute_runtime_graph_emits_ordered_lifecycle_events(monkeypatch) -> None:
    def decompose(state: dict[str, object]) -> dict[str, object]:
        return {
            "main_question": state["main_question"],
            "decomposition_sub_questions": ["What changed?"],
            "sub_question_artifacts": [],
            "citation_rows_by_index": {},
            "run_metadata": state["run_metadata"],
            "sub_qa": [],
            "output": "",
            "stage_snapshots": [],
        }

    builder = StateGraph(dict)
    builder.add_node("decompose", decompose)
    builder.add_edge(START, "decompose")
    builder.add_edge("decompose", END)
    graph = builder.compile()

    monkeypatch.setattr(
        "agent_search.runtime.graph.execution.build_runtime_graph",
        lambda *, context: graph,
    )

    emitted_events: list[RuntimeLifecycleEvent] = []
    state = execute_runtime_graph(
        context=RuntimeGraphContext(
            payload=RuntimeAgentRunRequest(query="What changed?"),
            model=object(),
            vector_store=object(),
            initial_search_context=[],
        ),
        run_metadata=_run_metadata(),
        lifecycle_callback=emitted_events.append,
    )

    assert state["main_question"] == "What changed?"
    assert [event.event_type for event in emitted_events] == [
        "run.started",
        "stage.started",
        "stage.updated",
        "stage.completed",
        "run.completed",
    ]
    assert [event.stage for event in emitted_events] == [
        "runtime",
        "decompose",
        "decompose",
        "decompose",
        "decompose",
    ]
