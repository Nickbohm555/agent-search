from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime.reducers import (
    merge_citation_rows_by_index,
    merge_decomposition_sub_questions,
    merge_stage_snapshots,
    merge_sub_qa,
    merge_sub_question_artifacts,
)
from schemas import CitationSourceRow, GraphStageSnapshot, SubQuestionAnswer, SubQuestionArtifacts


def _citation_row(*, citation_index: int, title: str, source: str = "wiki://doc") -> CitationSourceRow:
    return CitationSourceRow(
        citation_index=citation_index,
        rank=citation_index,
        title=title,
        source=source,
        content=f"Evidence for {title}",
        document_id=f"doc-{citation_index}",
        score=0.5 + (citation_index / 100),
    )


def _sub_qa(*, sub_question: str, sub_answer: str, expanded_query: str = "") -> SubQuestionAnswer:
    return SubQuestionAnswer(
        sub_question=sub_question,
        sub_answer=sub_answer,
        expanded_query=expanded_query,
        tool_call_input="{}",
        answerable=True,
        verification_reason="grounded",
    )


def _artifact(*, sub_question: str, expanded_queries: list[str], citation_index: int) -> SubQuestionArtifacts:
    row = _citation_row(citation_index=citation_index, title=f"{sub_question} doc")
    return SubQuestionArtifacts(
        sub_question=sub_question,
        expanded_queries=expanded_queries,
        retrieved_docs=[row],
        retrieval_provenance=[{"query": expanded_queries[0] if expanded_queries else sub_question}],
        reranked_docs=[row],
        sub_answer=f"Answer for {sub_question}",
        citation_rows_by_index={citation_index: row},
    )


def _snapshot(*, stage: str, sub_question: str = "", lane_index: int = 0) -> GraphStageSnapshot:
    return GraphStageSnapshot(
        stage=stage,
        status="completed",
        sub_question=sub_question,
        lane_index=lane_index,
        lane_total=2,
        decomposition_sub_questions=["Sub-question A?", "Sub-question B?"],
        sub_qa=[_sub_qa(sub_question="Sub-question A?", sub_answer="Answer A [1].")],
        sub_question_artifacts=[_artifact(sub_question="Sub-question A?", expanded_queries=["Sub-question A?"], citation_index=1)],
        output="Final [1].",
    )


def test_reducer_merge_decomposition_sub_questions_is_deterministic_and_deduplicated() -> None:
    current = ["Sub-question A?", "sub-question a?", " ", "Sub-question B?"]
    update = ["Sub-question C?", "Sub-question B?", "Sub-question A?"]

    results = [
        merge_decomposition_sub_questions(current, update)
        for _ in range(5)
    ]

    assert results == [["Sub-question A?", "Sub-question B?", "Sub-question C?"]] * 5
    assert current == ["Sub-question A?", "sub-question a?", " ", "Sub-question B?"]
    assert update == ["Sub-question C?", "Sub-question B?", "Sub-question A?"]


def test_reducer_merge_sub_question_artifacts_is_deterministic_and_last_write_wins() -> None:
    current = [
        _artifact(sub_question="Sub-question A?", expanded_queries=["A initial"], citation_index=1),
        _artifact(sub_question="Sub-question B?", expanded_queries=["B initial"], citation_index=2),
    ]
    update = [
        _artifact(sub_question="Sub-question B?", expanded_queries=["B updated"], citation_index=3),
        _artifact(sub_question="Sub-question C?", expanded_queries=["C initial"], citation_index=4),
    ]

    results = [merge_sub_question_artifacts(current, update) for _ in range(5)]
    serialized = [[item.model_dump(mode="json") for item in result] for result in results]

    assert serialized == [serialized[0]] * 5
    assert [item["sub_question"] for item in serialized[0]] == [
        "Sub-question A?",
        "Sub-question B?",
        "Sub-question C?",
    ]
    assert serialized[0][1]["expanded_queries"] == ["B updated"]
    assert current[1].expanded_queries == ["B initial"]


def test_reducer_merge_citation_rows_by_index_is_deterministic_and_sorted() -> None:
    current = {
        2: _citation_row(citation_index=2, title="Doc B"),
        1: _citation_row(citation_index=1, title="Doc A"),
    }
    update = {
        3: _citation_row(citation_index=3, title="Doc C"),
        2: _citation_row(citation_index=2, title="Doc B updated"),
    }

    results = [merge_citation_rows_by_index(current, update) for _ in range(5)]
    serialized = [
        {index: row.model_dump(mode="json") for index, row in result.items()}
        for result in results
    ]

    assert serialized == [serialized[0]] * 5
    assert list(results[0]) == [1, 2, 3]
    assert results[0][2].title == "Doc B updated"
    assert current[2].title == "Doc B"


def test_reducer_merge_sub_qa_is_deterministic_and_last_write_wins() -> None:
    current = [
        _sub_qa(sub_question="Sub-question A?", sub_answer="Old A"),
        _sub_qa(sub_question="Sub-question B?", sub_answer="Old B"),
    ]
    update = [
        _sub_qa(sub_question="Sub-question B?", sub_answer="New B", expanded_query="query-b"),
        _sub_qa(sub_question="Sub-question C?", sub_answer="New C"),
    ]

    results = [merge_sub_qa(current, update) for _ in range(5)]
    serialized = [[item.model_dump(mode="json") for item in result] for result in results]

    assert serialized == [serialized[0]] * 5
    assert [item["sub_question"] for item in serialized[0]] == [
        "Sub-question A?",
        "Sub-question B?",
        "Sub-question C?",
    ]
    assert serialized[0][1]["sub_answer"] == "New B"
    assert serialized[0][1]["expanded_query"] == "query-b"
    assert current[1].sub_answer == "Old B"


def test_reducer_merge_stage_snapshots_is_deterministic_and_append_only() -> None:
    current = [_snapshot(stage="decompose"), _snapshot(stage="expand", sub_question="Sub-question A?", lane_index=1)]
    update = [_snapshot(stage="answer", sub_question="Sub-question A?", lane_index=1)]

    results = [merge_stage_snapshots(current, update) for _ in range(5)]
    serialized = [[item.model_dump(mode="json") for item in result] for result in results]

    assert serialized == [serialized[0]] * 5
    assert [item["stage"] for item in serialized[0]] == ["decompose", "expand", "answer"]
    assert current[0].stage == "decompose"
