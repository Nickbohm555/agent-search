from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

from benchmarks.drb.export_raw_data import DRBExportSummary, export_internal_results_to_drb_jsonl
from benchmarks.drb.io_contract import InternalBenchmarkResultRecord

logger = logging.getLogger(__name__)

_REQUIRED_DRB_EXPORT_FIELDS = ("id", "prompt", "article")


class DRBAdvancedEvaluator(Protocol):
    """Deferred advanced evaluator extension point.

    TODO(section-35): Wire concrete RACE/FACT-equivalent adapters in future sections.
    """

    evaluator_id: str

    def evaluate_export(self, *, export_path: Path) -> dict[str, Any]:
        """Run advanced evaluator over exported DRB JSONL artifacts."""


@dataclass(frozen=True)
class DRBParitySmokeSummary:
    output_path: Path
    exported_count: int
    skipped_count: int
    required_fields: tuple[str, str, str]


def run_drb_export_parity_smoke(
    *,
    rows: Sequence[InternalBenchmarkResultRecord | dict[str, Any]],
    output_path: Path,
    include_errors: bool = False,
) -> DRBParitySmokeSummary:
    """Run DRB export-shape smoke parity check.

    This validates only required raw export schema compatibility.
    It intentionally does not attempt full evaluator parity.
    """

    logger.info(
        "Starting DRB parity smoke output_path=%s include_errors=%s row_count=%s",
        output_path,
        include_errors,
        len(rows),
    )
    summary = export_internal_results_to_drb_jsonl(
        rows=rows,
        output_path=output_path,
        include_errors=include_errors,
    )
    _validate_export_shape(output_path=output_path)
    smoke_summary = DRBParitySmokeSummary(
        output_path=summary.output_path,
        exported_count=summary.exported_count,
        skipped_count=summary.skipped_count,
        required_fields=_REQUIRED_DRB_EXPORT_FIELDS,
    )
    logger.info(
        "Completed DRB parity smoke output_path=%s exported_count=%s skipped_count=%s required_fields=%s",
        smoke_summary.output_path,
        smoke_summary.exported_count,
        smoke_summary.skipped_count,
        ",".join(smoke_summary.required_fields),
    )
    return smoke_summary


def run_deferred_advanced_evaluators(
    *,
    export_summary: DRBExportSummary | DRBParitySmokeSummary,
    evaluators: Sequence[DRBAdvancedEvaluator] | None = None,
) -> list[dict[str, Any]]:
    """Deferred advanced evaluator runner.

    TODO(section-35): Integrate with benchmark run orchestration once advanced evaluators are implemented.
    """

    if not evaluators:
        logger.info(
            "No deferred DRB advanced evaluators configured output_path=%s",
            export_summary.output_path,
        )
        return []

    results: list[dict[str, Any]] = []
    for evaluator in evaluators:
        payload = evaluator.evaluate_export(export_path=export_summary.output_path)
        results.append({"evaluator_id": evaluator.evaluator_id, "payload": payload})
        logger.info(
            "Deferred DRB advanced evaluator executed evaluator_id=%s output_path=%s",
            evaluator.evaluator_id,
            export_summary.output_path,
        )
    return results


def _validate_export_shape(*, output_path: Path) -> None:
    with output_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if set(payload.keys()) != set(_REQUIRED_DRB_EXPORT_FIELDS):
                raise ValueError(
                    "DRB export shape mismatch "
                    f"line={line_number} keys={sorted(payload.keys())} required={list(_REQUIRED_DRB_EXPORT_FIELDS)}"
                )

