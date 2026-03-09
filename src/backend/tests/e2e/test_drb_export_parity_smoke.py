from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from benchmarks.drb.parity_runner import run_drb_export_parity_smoke


def test_drb_export_parity_smoke_validates_required_shape(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    caplog.set_level("INFO")
    output_path = tmp_path / "drb_parity.jsonl"
    rows = [
        {
            "run_id": "run-parity-1",
            "mode": "agentic_default",
            "question_id": "DRB-001",
            "prompt": "What changed in the policy rollout?",
            "answer_payload": {"output": "The rollout shifted to phased deployment."},
            "execution_error": None,
        },
        {
            "run_id": "run-parity-1",
            "mode": "agentic_default",
            "question_id": "DRB-002",
            "prompt": "Which team approved the plan?",
            "answer_payload": {"output": "The operations committee approved the plan."},
            "execution_error": None,
        },
    ]

    summary = run_drb_export_parity_smoke(rows=rows, output_path=output_path)

    assert summary.exported_count == 2
    assert summary.skipped_count == 0
    assert summary.required_fields == ("id", "prompt", "article")
    assert "Starting DRB parity smoke" in caplog.text
    assert "Completed DRB parity smoke" in caplog.text

    with output_path.open("r", encoding="utf-8") as handle:
        exported_rows = [json.loads(line) for line in handle if line.strip()]

    assert len(exported_rows) == 2
    assert all(set(row.keys()) == {"id", "prompt", "article"} for row in exported_rows)
