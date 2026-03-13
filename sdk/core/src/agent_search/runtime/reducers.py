from __future__ import annotations

from collections.abc import Iterable, Mapping

from schemas import CitationSourceRow, GraphStageSnapshot, SubQuestionAnswer, SubQuestionArtifacts


def merge_decomposition_sub_questions(
    current: Iterable[str],
    update: Iterable[str],
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for sub_question in [*current, *update]:
        normalized = str(sub_question).strip()
        if not normalized:
            continue
        identity = normalized.casefold()
        if identity in seen:
            continue
        seen.add(identity)
        merged.append(normalized)
    return merged


def merge_sub_question_artifacts(
    current: Iterable[SubQuestionArtifacts],
    update: Iterable[SubQuestionArtifacts],
) -> list[SubQuestionArtifacts]:
    order: list[str] = []
    merged_by_sub_question: dict[str, SubQuestionArtifacts] = {}
    for artifact in [*current, *update]:
        key = artifact.sub_question
        if key not in merged_by_sub_question:
            order.append(key)
        merged_by_sub_question[key] = artifact.model_copy(deep=True)
    return [merged_by_sub_question[key] for key in order]


def merge_citation_rows_by_index(
    current: Mapping[int, CitationSourceRow],
    update: Mapping[int, CitationSourceRow],
) -> dict[int, CitationSourceRow]:
    merged: dict[int, CitationSourceRow] = {
        int(index): row.model_copy(deep=True) for index, row in current.items()
    }
    for index, row in update.items():
        merged[int(index)] = row.model_copy(deep=True)
    return {index: merged[index] for index in sorted(merged)}


def merge_sub_qa(
    current: Iterable[SubQuestionAnswer],
    update: Iterable[SubQuestionAnswer],
) -> list[SubQuestionAnswer]:
    order: list[str] = []
    merged_by_sub_question: dict[str, SubQuestionAnswer] = {}
    for item in [*current, *update]:
        key = item.sub_question
        if key not in merged_by_sub_question:
            order.append(key)
        merged_by_sub_question[key] = item.model_copy(deep=True)
    return [merged_by_sub_question[key] for key in order]


def merge_stage_snapshots(
    current: Iterable[GraphStageSnapshot],
    update: Iterable[GraphStageSnapshot],
) -> list[GraphStageSnapshot]:
    return [
        *(snapshot.model_copy(deep=True) for snapshot in current),
        *(snapshot.model_copy(deep=True) for snapshot in update),
    ]
