from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime import runner as runtime_runner
from agent_search.runtime.lifecycle_events import LifecycleEventBuilder
from schemas import GraphRunMetadata, RuntimeAgentRunRequest


def _run_metadata() -> GraphRunMetadata:
    return GraphRunMetadata(
        run_id="run-trace-correlation",
        thread_id="550e8400-e29b-41d4-a716-446655440100",
        trace_id="trace-trace-correlation",
        correlation_id="corr-trace-correlation",
    )


def _capture_trace_hooks(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[dict[str, object]]]:
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
    return captured


def _assert_same_correlation_tuple(metadata_records: list[dict[str, object]]) -> None:
    assert {
        (record["run_id"], record["thread_id"], record["trace_id"])
        for record in metadata_records
    } == {
        ("run-trace-correlation", "550e8400-e29b-41d4-a716-446655440100", "trace-trace-correlation")
    }


def test_trace_correlation_tuple_is_joinable_across_runtime_lifecycle_success_and_failure_events() -> None:
    builder = LifecycleEventBuilder(run_metadata=_run_metadata())

    success_events = [
        builder.emit_run_started(),
        *builder.consume_stream_signal("tasks", {"name": "search", "input": {"query": "joinability"}}),
        *builder.consume_stream_signal("updates", {"search": {"sub_question": "What changed?"}}),
        builder.emit_terminal(status="success"),
    ]
    failure_events = [
        builder.emit_run_started(),
        *builder.consume_stream_signal("tasks", {"name": "search", "input": {"query": "joinability"}}),
        *builder.consume_stream_signal("tasks", {"name": "search", "error": "backend timeout"}),
        builder.emit_terminal(status="error", error="backend timeout"),
    ]

    _assert_same_correlation_tuple([event.model_dump() for event in success_events])
    _assert_same_correlation_tuple([event.model_dump() for event in failure_events])
    assert success_events[-1].event_type == "run.completed"
    assert failure_events[-1].event_type == "run.failed"
    assert failure_events[-1].error == "backend timeout"


def test_trace_correlation_tuple_is_joinable_across_runtime_trace_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_trace_hooks(monkeypatch)
    run_metadata = _run_metadata()

    monkeypatch.setattr(
        runtime_runner.legacy_service,
        "build_graph_run_metadata",
        lambda thread_id=None: run_metadata,
    )
    monkeypatch.setattr(
        runtime_runner,
        "execute_runtime_graph",
        lambda **_kwargs: {
            "main_question": "How does success tracing work?",
            "decomposition_sub_questions": [],
            "sub_question_artifacts": [],
            "final_answer": "done",
            "citation_rows_by_index": {},
            "run_metadata": run_metadata,
            "sub_qa": [],
            "output": "done",
            "stage_snapshots": [],
        },
    )
    monkeypatch.setattr(
        runtime_runner.legacy_service,
        "map_graph_state_to_runtime_response",
        lambda _state: runtime_runner.RuntimeAgentRunResponse(
            main_question="How does success tracing work?",
            thread_id=run_metadata.thread_id,
            sub_items=[],
            output="done",
        ),
    )

    runtime_runner.run_runtime_agent(
        RuntimeAgentRunRequest(query="How does success tracing work?"),
        model=object(),
        vector_store=object(),
        langfuse_callback=object(),
    )

    trace_metadata = captured["traces"][0]["metadata"]
    terminal_metadata = captured["ends"][-1]["metadata"]

    _assert_same_correlation_tuple([trace_metadata, terminal_metadata])
    assert trace_metadata["stage"] == "runtime"
    assert trace_metadata["status"] == "running"
    assert terminal_metadata["stage"] == "runtime"
    assert terminal_metadata["status"] == "success"


def test_trace_correlation_tuple_is_joinable_across_runtime_trace_failure_path(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = _capture_trace_hooks(monkeypatch)
    run_metadata = _run_metadata()

    monkeypatch.setattr(
        runtime_runner.legacy_service,
        "build_graph_run_metadata",
        lambda thread_id=None: run_metadata,
    )
    monkeypatch.setattr(
        runtime_runner,
        "execute_runtime_graph",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("graph execution failed")),
    )

    with pytest.raises(RuntimeError, match="graph execution failed"):
        runtime_runner.run_runtime_agent(
            RuntimeAgentRunRequest(query="How does failure tracing work?"),
            model=object(),
            vector_store=object(),
            langfuse_callback=object(),
        )

    trace_metadata = captured["traces"][0]["metadata"]
    terminal_metadata = captured["ends"][-1]["metadata"]

    _assert_same_correlation_tuple([trace_metadata, terminal_metadata])
    assert trace_metadata["status"] == "running"
    assert terminal_metadata["stage"] == "runtime"
    assert terminal_metadata["status"] == "error"
