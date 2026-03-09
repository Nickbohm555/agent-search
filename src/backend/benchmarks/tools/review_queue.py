from __future__ import annotations

import argparse
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

ReviewDecision = Literal["approved", "rejected"]
ReviewStatus = Literal["pending_review", "approved", "rejected"]


class ReviewQueueRecord(BaseModel):
    """Candidate review queue row."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    candidate_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    expected_answer_points: list[str] = Field(min_length=1)
    required_sources: list[str] = Field(min_length=1)
    disallowed_behaviors: list[str] = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_url: str | None = None
    generator_model: str = Field(min_length=1)
    generation_prompt_version: str = Field(min_length=1)
    review_status: ReviewStatus = "pending_review"
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    review_reason: str | None = None


class ProvenanceLedgerRecord(BaseModel):
    """Immutable provenance event for human review decisions."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    candidate_id: str = Field(min_length=1)
    decision: ReviewDecision
    reviewer: str = Field(min_length=1)
    reviewed_at: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    source_url: str | None = None
    generator_model: str = Field(min_length=1)
    generation_prompt_version: str = Field(min_length=1)


class FrozenDatasetRecord(BaseModel):
    """Final dataset row schema used after review freeze."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    expected_answer_points: list[str] = Field(min_length=1)
    required_sources: list[str] = Field(min_length=1)
    disallowed_behaviors: list[str] = Field(min_length=1)


def load_review_queue(path: Path) -> list[ReviewQueueRecord]:
    records: list[ReviewQueueRecord] = []
    if not path.exists():
        return records

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            records.append(ReviewQueueRecord.model_validate_json(line))
    return records


def write_review_queue(path: Path, records: list[ReviewQueueRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row.model_dump(), ensure_ascii=True) + "\n")


def apply_review_decision(
    queue_path: Path,
    provenance_path: Path,
    *,
    candidate_id: str,
    decision: ReviewDecision,
    reviewer: str,
    reason: str,
) -> ReviewQueueRecord:
    """Apply human review decision and append immutable provenance event."""

    logger.info(
        "Applying review decision queue_path=%s provenance_path=%s candidate_id=%s decision=%s reviewer=%s",
        queue_path,
        provenance_path,
        candidate_id,
        decision,
        reviewer,
    )

    records = load_review_queue(queue_path)
    match = next((row for row in records if row.candidate_id == candidate_id), None)
    if match is None:
        raise ValueError(f"Unknown candidate_id={candidate_id}")

    if match.review_status != "pending_review":
        raise ValueError(
            f"Candidate {candidate_id} already reviewed with status={match.review_status}"
        )

    reviewed_at = datetime.now(UTC).isoformat()
    match.review_status = decision
    match.reviewed_by = reviewer
    match.reviewed_at = reviewed_at
    match.review_reason = reason

    write_review_queue(queue_path, records)

    provenance = ProvenanceLedgerRecord(
        candidate_id=match.candidate_id,
        decision=decision,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        reason=reason,
        source_id=match.source_id,
        source_title=match.source_title,
        source_url=match.source_url,
        generator_model=match.generator_model,
        generation_prompt_version=match.generation_prompt_version,
    )
    provenance_path.parent.mkdir(parents=True, exist_ok=True)
    with provenance_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(provenance.model_dump(), ensure_ascii=True) + "\n")

    logger.info(
        "Applied review decision candidate_id=%s new_status=%s provenance_path=%s",
        candidate_id,
        decision,
        provenance_path,
    )
    return match


def export_frozen_dataset(
    queue_path: Path,
    output_path: Path,
    *,
    question_id_prefix: str = "DRB",
    start_index: int = 1,
) -> list[FrozenDatasetRecord]:
    """Export approved questions to frozen dataset JSONL after review completion."""

    logger.info(
        "Exporting frozen dataset queue_path=%s output_path=%s question_id_prefix=%s start_index=%s",
        queue_path,
        output_path,
        question_id_prefix,
        start_index,
    )

    records = load_review_queue(queue_path)
    pending = [row for row in records if row.review_status == "pending_review"]
    if pending:
        raise ValueError("Cannot freeze dataset while pending_review candidates exist")

    approved = [row for row in records if row.review_status == "approved"]
    frozen: list[FrozenDatasetRecord] = []
    for offset, row in enumerate(sorted(approved, key=lambda item: item.candidate_id), start=start_index):
        frozen.append(
            FrozenDatasetRecord(
                question_id=f"{question_id_prefix}-{offset:03d}",
                question=row.question,
                domain=row.domain,
                difficulty=row.difficulty,
                expected_answer_points=row.expected_answer_points,
                required_sources=row.required_sources,
                disallowed_behaviors=row.disallowed_behaviors,
            )
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in frozen:
            handle.write(json.dumps(row.model_dump(), ensure_ascii=True) + "\n")

    logger.info("Exported frozen dataset output_path=%s record_count=%s", output_path, len(frozen))
    return frozen


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review and freeze generated benchmark questions.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    decide = subparsers.add_parser("decide", help="Apply human review decision to a candidate")
    decide.add_argument("--queue", type=Path, required=True)
    decide.add_argument("--provenance", type=Path, required=True)
    decide.add_argument("--candidate-id", required=True)
    decide.add_argument("--decision", choices=["approved", "rejected"], required=True)
    decide.add_argument("--reviewer", required=True)
    decide.add_argument("--reason", required=True)

    export = subparsers.add_parser("export", help="Export approved rows to frozen dataset")
    export.add_argument("--queue", type=Path, required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--question-id-prefix", default="DRB")
    export.add_argument("--start-index", type=int, default=1)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    args = _build_parser().parse_args(argv)

    if args.command == "decide":
        apply_review_decision(
            queue_path=args.queue,
            provenance_path=args.provenance,
            candidate_id=args.candidate_id,
            decision=args.decision,
            reviewer=args.reviewer,
            reason=args.reason,
        )
        return 0

    if args.command == "export":
        export_frozen_dataset(
            queue_path=args.queue,
            output_path=args.output,
            question_id_prefix=args.question_id_prefix,
            start_index=args.start_index,
        )
        return 0

    raise ValueError(f"Unknown command={args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
