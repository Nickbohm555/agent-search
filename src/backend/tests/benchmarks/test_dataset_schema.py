from __future__ import annotations

import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from benchmarks.datasets import load_benchmark_questions

DATASET_PATH = BACKEND_ROOT / "benchmarks" / "datasets" / "internal_v1" / "questions.jsonl"

EXPECTED_FIELDS = {
    "question_id",
    "question",
    "domain",
    "difficulty",
    "expected_answer_points",
    "required_sources",
    "disallowed_behaviors",
}


def _raw_rows() -> list[dict[str, object]]:
    with DATASET_PATH.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def test_dataset_schema_and_size_are_valid() -> None:
    questions = load_benchmark_questions(DATASET_PATH)

    assert len(questions) == 120


def test_dataset_rows_use_strict_required_fields_only() -> None:
    for row in _raw_rows():
        assert set(row.keys()) == EXPECTED_FIELDS


def test_dataset_question_ids_are_unique_and_well_formed() -> None:
    questions = load_benchmark_questions(DATASET_PATH)

    ids = [question.question_id for question in questions]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"DRB-\d{3}", value) for value in ids)


def test_dataset_domain_and_difficulty_distribution() -> None:
    questions = load_benchmark_questions(DATASET_PATH)

    domain_counts = Counter(question.domain for question in questions)
    difficulty_counts = Counter(question.difficulty for question in questions)

    assert len(domain_counts) == 10
    assert set(domain_counts.values()) == {12}
    assert difficulty_counts == Counter({"easy": 40, "medium": 40, "hard": 40})


def test_dataset_loader_emits_visibility_logs(caplog) -> None:
    caplog.set_level(logging.INFO)

    load_benchmark_questions(DATASET_PATH)

    assert "Loading benchmark dataset" in caplog.text
    assert "Loaded benchmark dataset" in caplog.text
