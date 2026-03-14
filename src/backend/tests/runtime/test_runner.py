from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime.runner import _resolve_checkpoint_config_id
from schemas import GraphRunMetadata, RuntimeSubquestionDecision, RuntimeSubquestionResumeEnvelope


def test_resolve_checkpoint_config_id_prefers_resume_checkpoint_for_hitl_resume() -> None:
    run_metadata = GraphRunMetadata(
        run_id="run-123",
        thread_id="550e8400-e29b-41d4-a716-446655440000",
        trace_id="trace-123",
        correlation_id="corr-123",
    )
    resume = RuntimeSubquestionResumeEnvelope(
        checkpoint_id="checkpoint-live",
        decisions=[RuntimeSubquestionDecision(subquestion_id="sq-1", action="skip")],
    )

    resolved = _resolve_checkpoint_config_id(run_metadata, resume)

    assert resolved == "checkpoint-live"


def test_resolve_checkpoint_config_id_falls_back_to_thread_id_without_typed_resume() -> None:
    run_metadata = GraphRunMetadata(
        run_id="run-123",
        thread_id="550e8400-e29b-41d4-a716-446655440000",
        trace_id="trace-123",
        correlation_id="corr-123",
    )

    resolved = _resolve_checkpoint_config_id(run_metadata, {"approved": True})

    assert resolved == "550e8400-e29b-41d4-a716-446655440000"
