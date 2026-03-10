from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from config import benchmarks_enabled
from db import SessionLocal
from models import BenchmarkResult, BenchmarkRun, BenchmarkRunMode
from services.benchmark_jobs import get_benchmark_run_status

logger = logging.getLogger(__name__)


def _to_iso8601_or_none(timestamp: datetime | None) -> str | None:
    if timestamp is None:
        return None
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC).isoformat()
    return timestamp.astimezone(UTC).isoformat()


def _resolve_run_id(db: Session, run_id: str | None) -> str | None:
    if run_id:
        return run_id
    latest_run_id = db.scalar(select(BenchmarkRun.run_id).order_by(BenchmarkRun.created_at.desc()).limit(1))
    if latest_run_id is None:
        return None
    return str(latest_run_id)


def _default_output_path(run_id: str) -> Path:
    return Path("benchmarks") / "exports" / f"{run_id}.json"


def export_run_to_json(*, db: Session, run_id: str, output_path: Path) -> dict[str, Any]:
    run = db.get(BenchmarkRun, run_id)
    if run is None:
        raise ValueError(f"Benchmark run not found: {run_id}")

    status_payload = get_benchmark_run_status(run_id=run_id, db=db)
    if status_payload is None:
        raise ValueError(f"Benchmark run status unavailable: {run_id}")

    mode_rows = db.scalars(select(BenchmarkRunMode).where(BenchmarkRunMode.run_id == run_id).order_by(BenchmarkRunMode.mode)).all()
    result_rows = db.scalars(
        select(BenchmarkResult).where(BenchmarkResult.run_id == run_id).order_by(BenchmarkResult.mode, BenchmarkResult.question_id)
    ).all()

    payload = {
        "exported_at": datetime.now(tz=UTC).isoformat(),
        "run_id": run_id,
        "run": {
            "status": run.status,
            "dataset_id": run.dataset_id,
            "created_at": _to_iso8601_or_none(run.created_at),
            "started_at": _to_iso8601_or_none(run.started_at),
            "finished_at": _to_iso8601_or_none(run.finished_at),
            "error": run.error,
            "slo_snapshot": run.slo_snapshot,
            "objective_snapshot": run.objective_snapshot,
            "context_fingerprint": run.context_fingerprint,
            "corpus_hash": run.corpus_hash,
            "run_metadata": run.run_metadata,
            "modes": [row.mode for row in mode_rows],
        },
        "status_summary": status_payload.model_dump(mode="json"),
        "results_raw": [
            {
                "id": row.id,
                "run_id": row.run_id,
                "mode": row.mode,
                "question_id": row.question_id,
                "latency_ms": row.latency_ms,
                "e2e_latency_ms": row.e2e_latency_ms,
                "timing_outcome": row.timing_outcome,
                "execution_error": row.execution_error,
                "stage_timings": row.stage_timings,
                "token_usage": row.token_usage,
                "citations": row.citations,
                "answer_payload": row.answer_payload,
                "created_at": _to_iso8601_or_none(row.created_at),
            }
            for row in result_rows
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    logger.info(
        "Benchmark export cli wrote JSON run_id=%s output_path=%s mode_count=%s result_count=%s",
        run_id,
        output_path,
        len(mode_rows),
        len(result_rows),
    )
    return {
        "run_id": run_id,
        "output_path": str(output_path),
        "mode_count": len(mode_rows),
        "result_count": len(result_rows),
        "status": run.status,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export benchmark run artifacts to JSON.")
    parser.add_argument("--run-id", default=None, help="Run id to export. Latest run is used when omitted.")
    parser.add_argument("--output", type=Path, default=None, help="Output JSON path. Defaults to benchmarks/exports/<run_id>.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    args = _build_parser().parse_args(argv)
    if not benchmarks_enabled():
        raise SystemExit("Benchmarking is disabled. Set BENCHMARKS_ENABLED=true to run benchmark CLI commands.")

    with SessionLocal() as db:
        run_id = _resolve_run_id(db, args.run_id)
        if run_id is None:
            raise SystemExit("No benchmark runs available to export.")

        output_path = args.output or _default_output_path(run_id)
        logger.info("Benchmark export cli requested run_id=%s output_path=%s", run_id, output_path)
        summary = export_run_to_json(db=db, run_id=run_id, output_path=output_path)

    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
