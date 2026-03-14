from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel

from schemas import GraphRunMetadata, RuntimeAgentRunResponse, SubQuestionAnswer, SubQuestionArtifacts
from utils.langfuse_tracing import build_trace_metadata


class RuntimeLifecycleEvent(BaseModel):
    event_type: str
    event_id: str
    run_id: str
    thread_id: str
    trace_id: str
    stage: str
    status: str
    emitted_at: str
    error: str | None = None
    decomposition_sub_questions: list[str] | None = None
    sub_question_artifacts: list[SubQuestionArtifacts] | None = None
    sub_qa: list[SubQuestionAnswer] | None = None
    output: str | None = None
    result: RuntimeAgentRunResponse | None = None
    interrupt_payload: Any | None = None
    checkpoint_id: str | None = None
    elapsed_ms: int | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_stage_name(stage_name: str | None) -> str:
    normalized = (stage_name or "").strip()
    if not normalized:
        return "runtime"
    if normalized == "synthesize":
        return "synthesize_final"
    if normalized == "subquestion_checkpoint":
        return "subquestions_ready"
    return normalized


class LifecycleEventBuilder:
    def __init__(
        self,
        *,
        run_metadata: GraphRunMetadata,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._run_metadata = run_metadata
        self._clock = clock
        self._sequence = 0
        self._active_stage = "runtime"

    @property
    def active_stage(self) -> str:
        return self._active_stage

    def emit_run_started(self) -> RuntimeLifecycleEvent:
        return self._emit(event_type="run.started", stage="runtime", status="running")

    def emit_recovery_started(self, *, checkpoint_id: str | None = None) -> RuntimeLifecycleEvent:
        error = None
        if checkpoint_id:
            error = f"resuming from checkpoint {checkpoint_id}"
        return self._emit(event_type="run.recovered", stage="recovery", status="running", error=error)

    def emit_retrying(self, *, stage: str, error: str) -> RuntimeLifecycleEvent:
        normalized_stage = _normalize_stage_name(stage)
        self._active_stage = normalized_stage
        return self._emit(event_type="stage.retrying", stage=normalized_stage, status="retrying", error=error)

    def emit_terminal(self, *, status: str, error: str | None = None) -> RuntimeLifecycleEvent:
        event_type = {
            "success": "run.completed",
            "completed": "run.completed",
            "error": "run.failed",
            "failed": "run.failed",
            "paused": "run.paused",
        }.get(status, "run.completed")
        return self._emit(event_type=event_type, stage=self._active_stage, status=status, error=error)

    def consume_stream_signal(self, mode: str, payload: Any) -> list[RuntimeLifecycleEvent]:
        if not isinstance(payload, Mapping):
            return []
        if mode == "tasks":
            return self._consume_task_signal(payload)
        if mode == "updates":
            return self._consume_update_signal(payload)
        if mode == "checkpoints":
            return self._consume_checkpoint_signal(payload)
        return []

    def _consume_task_signal(self, payload: Mapping[str, Any]) -> list[RuntimeLifecycleEvent]:
        stage = _normalize_stage_name(str(payload.get("name", "")))
        if "input" in payload:
            self._active_stage = stage
            return [self._emit(event_type="stage.started", stage=stage, status="running")]
        if payload.get("error"):
            self._active_stage = stage
            return [self._emit(event_type="stage.failed", stage=stage, status="error", error=str(payload["error"]))]
        interrupts = payload.get("interrupts")
        if isinstance(interrupts, list) and interrupts:
            self._active_stage = stage
            return [self._emit(event_type="stage.interrupted", stage=stage, status="paused")]
        self._active_stage = stage
        return [self._emit(event_type="stage.completed", stage=stage, status="completed")]

    def _consume_update_signal(self, payload: Mapping[str, Any]) -> list[RuntimeLifecycleEvent]:
        events: list[RuntimeLifecycleEvent] = []
        for stage_name in payload:
            if str(stage_name).startswith("__"):
                continue
            stage = _normalize_stage_name(str(stage_name))
            self._active_stage = stage
            events.append(self._emit(event_type="stage.updated", stage=stage, status="running"))
        return events

    def _consume_checkpoint_signal(self, payload: Mapping[str, Any]) -> list[RuntimeLifecycleEvent]:
        metadata = payload.get("metadata")
        if not isinstance(metadata, Mapping):
            return []
        source = str(metadata.get("source", "")).strip()
        if source == "input":
            return []
        config = payload.get("config")
        checkpoint_id = None
        if isinstance(config, Mapping):
            configurable = config.get("configurable")
            if isinstance(configurable, Mapping):
                raw_checkpoint_id = configurable.get("checkpoint_id")
                if raw_checkpoint_id is not None:
                    checkpoint_id = str(raw_checkpoint_id)
        next_nodes = payload.get("next")
        stage = self._active_stage
        if isinstance(next_nodes, list) and next_nodes:
            stage = _normalize_stage_name(str(next_nodes[0]))
        self._active_stage = stage
        return [
            self._emit(
                event_type="checkpoint.created",
                stage=stage,
                status="checkpointed",
                error=f"checkpoint_id={checkpoint_id}" if checkpoint_id else None,
                checkpoint_id=checkpoint_id,
            )
        ]

    def _emit(
        self,
        *,
        event_type: str,
        stage: str,
        status: str,
        error: str | None = None,
        decomposition_sub_questions: list[str] | None = None,
        sub_question_artifacts: list[SubQuestionArtifacts] | None = None,
        sub_qa: list[SubQuestionAnswer] | None = None,
        output: str | None = None,
        result: RuntimeAgentRunResponse | None = None,
        interrupt_payload: Any | None = None,
        checkpoint_id: str | None = None,
        elapsed_ms: int | None = None,
    ) -> RuntimeLifecycleEvent:
        self._sequence += 1
        emitted_at = self._clock().isoformat()
        metadata = build_trace_metadata(
            run_metadata=self._run_metadata,
            stage=stage,
            status=status,
        )
        return RuntimeLifecycleEvent(
            event_type=event_type,
            event_id=f"{self._run_metadata.run_id}:{self._sequence:06d}",
            run_id=str(metadata["run_id"]),
            thread_id=str(metadata["thread_id"]),
            trace_id=str(metadata["trace_id"]),
            stage=str(metadata["stage"]),
            status=str(metadata["status"]),
            emitted_at=emitted_at,
            error=error,
            decomposition_sub_questions=decomposition_sub_questions,
            sub_question_artifacts=sub_question_artifacts,
            sub_qa=sub_qa,
            output=output,
            result=result,
            interrupt_payload=interrupt_payload,
            checkpoint_id=checkpoint_id,
            elapsed_ms=elapsed_ms,
        )


__all__ = ["LifecycleEventBuilder", "RuntimeLifecycleEvent"]
