from __future__ import annotations

import json
import logging
from typing import Any, Annotated

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

NonEmptyStr = Annotated[str, Field(min_length=1)]


class DRBRawRecord(BaseModel):
    """DeepResearchBench-inspired raw record contract."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: NonEmptyStr
    prompt: NonEmptyStr
    article: NonEmptyStr


class InternalBenchmarkResultRecord(BaseModel):
    """Internal benchmark result row used by DRB export mapping."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    run_id: NonEmptyStr
    mode: NonEmptyStr
    question_id: NonEmptyStr
    prompt: NonEmptyStr
    answer_payload: dict[str, Any] | None = None
    execution_error: str | None = None


def build_drb_record_id(*, run_id: str, mode: str, question_id: str) -> str:
    return f"{run_id}:{mode}:{question_id}"


def map_internal_result_to_drb_record(
    row: InternalBenchmarkResultRecord,
    *,
    include_errors: bool = False,
) -> DRBRawRecord:
    """Map internal benchmark result row into DRB-inspired raw record."""

    article = _resolve_article(row.answer_payload)
    if not article:
        if include_errors and row.execution_error:
            article = f"[execution_error] {row.execution_error}"
        else:
            raise ValueError(
                "Cannot export DRB record without answer article text. "
                f"run_id={row.run_id} mode={row.mode} question_id={row.question_id}"
            )

    record = DRBRawRecord(
        id=build_drb_record_id(run_id=row.run_id, mode=row.mode, question_id=row.question_id),
        prompt=row.prompt,
        article=article,
    )
    logger.info(
        "Mapped internal benchmark row to DRB record id=%s run_id=%s mode=%s question_id=%s",
        record.id,
        row.run_id,
        row.mode,
        row.question_id,
    )
    return record


def _resolve_article(answer_payload: dict[str, Any] | None) -> str:
    if not isinstance(answer_payload, dict):
        return ""

    output = answer_payload.get("output")
    if isinstance(output, str) and output.strip():
        return output.strip()

    # Fallback for non-standard payloads: preserve a serialized shape for visibility.
    payload_json = json.dumps(answer_payload, ensure_ascii=True, sort_keys=True).strip()
    return payload_json if payload_json not in {"", "{}"} else ""
