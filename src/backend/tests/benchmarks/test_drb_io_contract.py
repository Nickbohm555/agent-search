from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from benchmarks.drb.export_raw_data import export_internal_results_to_drb_jsonl
from benchmarks.drb.io_contract import (
    DRBRawRecord,
    InternalBenchmarkResultRecord,
    build_drb_record_id,
    map_internal_result_to_drb_record,
)


def test_drb_raw_record_requires_id_prompt_article() -> None:
    with pytest.raises(ValidationError):
        DRBRawRecord.model_validate({"id": "x", "prompt": "question only"})

    with pytest.raises(ValidationError):
        DRBRawRecord.model_validate({"id": "", "prompt": "p", "article": "a"})


def test_internal_result_maps_to_required_drb_fields() -> None:
    internal = InternalBenchmarkResultRecord(
        run_id="benchmark-run-1",
        mode="agentic_default",
        question_id="DRB-001",
        prompt="What changed in policy?",
        answer_payload={"output": "The policy added stricter review gates."},
    )

    record = map_internal_result_to_drb_record(internal)

    assert record.id == build_drb_record_id(
        run_id="benchmark-run-1",
        mode="agentic_default",
        question_id="DRB-001",
    )
    assert record.prompt == "What changed in policy?"
    assert record.article == "The policy added stricter review gates."


def test_export_writes_required_drb_fields_and_logs(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    caplog.set_level("INFO")
    output_path = tmp_path / "drb_raw.jsonl"

    rows = [
        {
            "run_id": "benchmark-run-2",
            "mode": "agentic_default",
            "question_id": "DRB-010",
            "prompt": "Who approved the budget?",
            "answer_payload": {"output": "The council approved the budget unanimously."},
            "execution_error": None,
        },
        {
            "run_id": "benchmark-run-2",
            "mode": "agentic_default",
            "question_id": "DRB-011",
            "prompt": "What was the implementation timeline?",
            "answer_payload": None,
            "execution_error": "runtime timeout",
        },
    ]

    summary = export_internal_results_to_drb_jsonl(rows, output_path=output_path)

    assert summary.exported_count == 1
    assert summary.skipped_count == 1
    assert "Starting DRB raw export" in caplog.text
    assert "Completed DRB raw export" in caplog.text
    assert "Skipping DRB export row" in caplog.text

    with output_path.open("r", encoding="utf-8") as handle:
        exported_rows = [json.loads(line) for line in handle if line.strip()]

    assert len(exported_rows) == 1
    assert set(exported_rows[0].keys()) == {"id", "prompt", "article"}
    assert exported_rows[0]["id"] == "benchmark-run-2:agentic_default:DRB-010"
