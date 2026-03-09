from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from benchmarks.drb.io_contract import (
    DRBRawRecord,
    InternalBenchmarkResultRecord,
    map_internal_result_to_drb_record,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DRBExportSummary:
    output_path: Path
    exported_count: int
    skipped_count: int


def export_internal_results_to_drb_jsonl(
    rows: Iterable[InternalBenchmarkResultRecord | dict[str, Any]],
    *,
    output_path: Path,
    include_errors: bool = False,
) -> DRBExportSummary:
    """Export internal benchmark result rows to DRB-inspired JSONL records."""

    logger.info(
        "Starting DRB raw export output_path=%s include_errors=%s",
        output_path,
        include_errors,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    exported = 0
    skipped = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for raw_row in rows:
            row = (
                raw_row
                if isinstance(raw_row, InternalBenchmarkResultRecord)
                else InternalBenchmarkResultRecord.model_validate(raw_row)
            )
            try:
                record = map_internal_result_to_drb_record(row, include_errors=include_errors)
            except ValueError as exc:
                skipped += 1
                logger.warning(
                    "Skipping DRB export row run_id=%s mode=%s question_id=%s reason=%s",
                    row.run_id,
                    row.mode,
                    row.question_id,
                    exc,
                )
                continue

            _write_jsonl_row(handle, record)
            exported += 1

    logger.info(
        "Completed DRB raw export output_path=%s exported_count=%s skipped_count=%s",
        output_path,
        exported,
        skipped,
    )
    return DRBExportSummary(output_path=output_path, exported_count=exported, skipped_count=skipped)


def _write_jsonl_row(handle, record: DRBRawRecord) -> None:  # noqa: ANN001
    handle.write(json.dumps(record.model_dump(mode="json"), ensure_ascii=True) + "\n")
