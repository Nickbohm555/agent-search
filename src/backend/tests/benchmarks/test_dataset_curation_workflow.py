from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from benchmarks.tools.generate_questions import generate_candidates_from_corpus
from benchmarks.tools.review_queue import (
    apply_review_decision,
    export_frozen_dataset,
    load_review_queue,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def _fake_invoker(_: str) -> str:
    return json.dumps(
        [
            {
                "question": "What policy did the city pass in 2025?",
                "domain": "policy",
                "difficulty": "medium",
                "expected_answer_points": ["year", "policy name"],
                "required_sources": ["city bulletin"],
                "disallowed_behaviors": ["fabricated citations"],
            },
            {
                "question": "Who voted against the policy and why?",
                "domain": "policy",
                "difficulty": "hard",
                "expected_answer_points": ["member name", "stated rationale"],
                "required_sources": ["meeting transcript"],
                "disallowed_behaviors": ["unsupported claims"],
            },
        ]
    )


def test_generation_creates_pending_review_candidates_with_logs(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    corpus_path = tmp_path / "public_corpus.jsonl"
    queue_path = tmp_path / "review_queue.jsonl"

    _write_jsonl(
        corpus_path,
        [
            {
                "id": "doc-001",
                "title": "City Bulletin",
                "article": "The city council approved a housing policy.",
                "url": "https://example.org/city-bulletin",
            }
        ],
    )

    caplog.set_level("INFO")
    candidates = generate_candidates_from_corpus(
        corpus_path=corpus_path,
        output_path=queue_path,
        invoke_model=_fake_invoker,
    )

    assert len(candidates) == 2
    assert all(candidate.review_status == "pending_review" for candidate in candidates)
    assert all(candidate.candidate_id.startswith("cand-") for candidate in candidates)
    assert "Starting candidate generation" in caplog.text
    assert "Completed candidate generation" in caplog.text

    queue_rows = load_review_queue(queue_path)
    assert len(queue_rows) == 2


def test_review_decision_transitions_and_provenance_append(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue.jsonl"
    provenance_path = tmp_path / "provenance.jsonl"

    _write_jsonl(
        queue_path,
        [
            {
                "candidate_id": "cand-1",
                "question": "What changed?",
                "domain": "policy",
                "difficulty": "easy",
                "expected_answer_points": ["policy"],
                "required_sources": ["source A"],
                "disallowed_behaviors": ["hallucination"],
                "source_id": "doc-1",
                "source_title": "Doc 1",
                "source_url": "https://example.org/doc-1",
                "generator_model": "gpt-4.1-mini",
                "generation_prompt_version": "v1",
                "review_status": "pending_review",
            }
        ],
    )

    updated = apply_review_decision(
        queue_path=queue_path,
        provenance_path=provenance_path,
        candidate_id="cand-1",
        decision="approved",
        reviewer="alice",
        reason="well-grounded",
    )

    assert updated.review_status == "approved"
    assert updated.reviewed_by == "alice"
    assert updated.reviewed_at is not None

    rows = load_review_queue(queue_path)
    assert rows[0].review_status == "approved"

    with provenance_path.open("r", encoding="utf-8") as handle:
        provenance_rows = [json.loads(line) for line in handle if line.strip()]

    assert len(provenance_rows) == 1
    assert provenance_rows[0]["candidate_id"] == "cand-1"
    assert provenance_rows[0]["decision"] == "approved"

    with pytest.raises(ValueError, match="already reviewed"):
        apply_review_decision(
            queue_path=queue_path,
            provenance_path=provenance_path,
            candidate_id="cand-1",
            decision="rejected",
            reviewer="bob",
            reason="second pass",
        )


def test_export_requires_no_pending_and_writes_dataset_rows(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue.jsonl"
    output_path = tmp_path / "questions.jsonl"

    _write_jsonl(
        queue_path,
        [
            {
                "candidate_id": "cand-b",
                "question": "Approved Q1",
                "domain": "economics",
                "difficulty": "medium",
                "expected_answer_points": ["point-1"],
                "required_sources": ["source-1"],
                "disallowed_behaviors": ["hallucination"],
                "source_id": "doc-b",
                "source_title": "Doc B",
                "source_url": None,
                "generator_model": "gpt-4.1-mini",
                "generation_prompt_version": "v1",
                "review_status": "approved",
                "reviewed_by": "alice",
                "reviewed_at": "2026-03-09T00:00:00+00:00",
                "review_reason": "good",
            },
            {
                "candidate_id": "cand-a",
                "question": "Approved Q2",
                "domain": "science",
                "difficulty": "hard",
                "expected_answer_points": ["point-2"],
                "required_sources": ["source-2"],
                "disallowed_behaviors": ["fabrication"],
                "source_id": "doc-a",
                "source_title": "Doc A",
                "source_url": None,
                "generator_model": "gpt-4.1-mini",
                "generation_prompt_version": "v1",
                "review_status": "approved",
                "reviewed_by": "alice",
                "reviewed_at": "2026-03-09T00:00:00+00:00",
                "review_reason": "good",
            },
        ],
    )

    frozen_rows = export_frozen_dataset(queue_path=queue_path, output_path=output_path)

    assert [row.question_id for row in frozen_rows] == ["DRB-001", "DRB-002"]
    assert [row.question for row in frozen_rows] == ["Approved Q2", "Approved Q1"]

    with output_path.open("r", encoding="utf-8") as handle:
        dataset_rows = [json.loads(line) for line in handle if line.strip()]

    assert set(dataset_rows[0].keys()) == {
        "question_id",
        "question",
        "domain",
        "difficulty",
        "expected_answer_points",
        "required_sources",
        "disallowed_behaviors",
    }


def test_export_fails_if_pending_candidates_exist(tmp_path: Path) -> None:
    queue_path = tmp_path / "review_queue.jsonl"
    output_path = tmp_path / "questions.jsonl"

    _write_jsonl(
        queue_path,
        [
            {
                "candidate_id": "cand-1",
                "question": "Pending row",
                "domain": "policy",
                "difficulty": "easy",
                "expected_answer_points": ["policy"],
                "required_sources": ["source"],
                "disallowed_behaviors": ["hallucination"],
                "source_id": "doc-1",
                "source_title": "Doc 1",
                "source_url": None,
                "generator_model": "gpt-4.1-mini",
                "generation_prompt_version": "v1",
                "review_status": "pending_review",
            }
        ],
    )

    with pytest.raises(ValueError, match="pending_review"):
        export_frozen_dataset(queue_path=queue_path, output_path=output_path)
