from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

NonEmptyStr = Annotated[str, Field(min_length=1)]


class BenchmarkQuestion(BaseModel):
    """Strict schema for one benchmark question JSONL row."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question_id: NonEmptyStr
    question: NonEmptyStr
    domain: NonEmptyStr
    difficulty: NonEmptyStr
    expected_answer_points: list[NonEmptyStr] = Field(min_length=1)
    required_sources: list[NonEmptyStr] = Field(min_length=1)
    disallowed_behaviors: list[NonEmptyStr] = Field(min_length=1)


def load_benchmark_questions(path: Path) -> list[BenchmarkQuestion]:
    """Load and validate a benchmark JSONL file with strict row schemas."""

    logger.info("Loading benchmark dataset from path=%s", path)
    questions: list[BenchmarkQuestion] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.error(
                    "Invalid benchmark dataset JSON at path=%s line=%s error=%s",
                    path,
                    line_no,
                    exc,
                )
                raise ValueError(f"Invalid JSON at line {line_no}") from exc

            try:
                questions.append(BenchmarkQuestion.model_validate(payload))
            except Exception as exc:
                logger.error(
                    "Invalid benchmark dataset schema at path=%s line=%s error=%s",
                    path,
                    line_no,
                    exc,
                )
                raise ValueError(f"Invalid benchmark schema at line {line_no}") from exc

    logger.info("Loaded benchmark dataset path=%s question_count=%s", path, len(questions))
    return questions
