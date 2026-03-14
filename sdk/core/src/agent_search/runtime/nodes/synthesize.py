from __future__ import annotations

import logging
import re
from typing import Any, Callable

from schemas import SubQuestionAnswer, SubQuestionArtifacts, SynthesizeFinalNodeInput, SynthesizeFinalNodeOutput
from services.initial_answer_service import generate_final_synthesis_answer

logger = logging.getLogger(__name__)

_QUERY_LOG_MAX = 200
_INITIAL_ANSWER_FALLBACK_PREFIX = "Partial context only."
_CITATION_INDEX_PATTERN = re.compile(r"\[(\d+)\]")


def _truncate_query(q: str) -> str:
    return q[: _QUERY_LOG_MAX] + "..." if len(q) > _QUERY_LOG_MAX else q


def _extract_citation_indices(answer: str) -> list[int]:
    if not answer:
        return []
    seen: set[int] = set()
    indices: list[int] = []
    for raw_index in _CITATION_INDEX_PATTERN.findall(answer):
        try:
            index = int(raw_index)
        except ValueError:
            continue
        if index <= 0 or index in seen:
            continue
        seen.add(index)
        indices.append(index)
    return indices


def _build_initial_answer_timeout_fallback(sub_qa: list[SubQuestionAnswer]) -> str:
    partial_answers = [item.sub_answer.strip() for item in sub_qa if isinstance(item.sub_answer, str) and item.sub_answer.strip()]
    if not partial_answers:
        return _INITIAL_ANSWER_FALLBACK_PREFIX
    joined = " ".join(partial_answers)
    return f"{_INITIAL_ANSWER_FALLBACK_PREFIX} {joined}"


def _collect_available_citation_indices(sub_question_artifacts: list[SubQuestionArtifacts]) -> set[int]:
    available_indices: set[int] = set()
    for artifact in sub_question_artifacts:
        for index in artifact.citation_rows_by_index.keys():
            if index > 0:
                available_indices.add(index)
    return available_indices


def _build_final_synthesis_citation_fallback(
    *,
    sub_qa: list[SubQuestionAnswer],
    available_indices: set[int],
    extract_citation_indices_fn: Callable[[str], list[int]],
    build_initial_answer_timeout_fallback_fn: Callable[[list[SubQuestionAnswer]], str],
) -> str:
    fallback_candidates: list[str] = []
    seen_answers: set[str] = set()
    for answerable_only in (True, False):
        for item in sub_qa:
            if answerable_only and not item.answerable:
                continue
            answer = (item.sub_answer or "").strip()
            if not answer:
                continue
            citation_indices = extract_citation_indices_fn(answer)
            if not citation_indices:
                continue
            if available_indices and any(index not in available_indices for index in citation_indices):
                continue
            normalized_answer = answer.casefold()
            if normalized_answer in seen_answers:
                continue
            seen_answers.add(normalized_answer)
            fallback_candidates.append(answer)
            if len(fallback_candidates) >= 2:
                return " ".join(fallback_candidates)
    if fallback_candidates:
        return " ".join(fallback_candidates)
    return build_initial_answer_timeout_fallback_fn(sub_qa)


def _enforce_final_synthesis_citation_contract(
    *,
    generated_final_answer: str,
    sub_qa: list[SubQuestionAnswer],
    sub_question_artifacts: list[SubQuestionArtifacts],
    run_id: str,
    extract_citation_indices_fn: Callable[[str], list[int]],
    build_initial_answer_timeout_fallback_fn: Callable[[list[SubQuestionAnswer]], str],
) -> str:
    resolved_final_answer = (generated_final_answer or "").strip()
    if not resolved_final_answer:
        logger.warning(
            "Final synthesis citation contract fallback; generated answer empty run_id=%s",
            run_id,
        )
        available_indices = _collect_available_citation_indices(sub_question_artifacts)
        return _build_final_synthesis_citation_fallback(
            sub_qa=sub_qa,
            available_indices=available_indices,
            extract_citation_indices_fn=extract_citation_indices_fn,
            build_initial_answer_timeout_fallback_fn=build_initial_answer_timeout_fallback_fn,
        )

    available_indices = _collect_available_citation_indices(sub_question_artifacts)
    citation_indices_used = extract_citation_indices_fn(resolved_final_answer)
    invalid_indices = (
        [index for index in citation_indices_used if index not in available_indices]
        if available_indices
        else []
    )
    missing_citations = not citation_indices_used

    if not missing_citations and not invalid_indices:
        return resolved_final_answer

    fallback_reason = "missing_citation_markers" if missing_citations else "missing_supporting_source_rows"
    logger.warning(
        "Final synthesis citation contract fallback; reason=%s used_indices=%s available_indices_count=%s run_id=%s",
        fallback_reason,
        citation_indices_used,
        len(available_indices),
        run_id,
    )
    return _build_final_synthesis_citation_fallback(
        sub_qa=sub_qa,
        available_indices=available_indices,
        extract_citation_indices_fn=extract_citation_indices_fn,
        build_initial_answer_timeout_fallback_fn=build_initial_answer_timeout_fallback_fn,
    )


def run_synthesize_node(
    *,
    node_input: SynthesizeFinalNodeInput,
    callbacks: list[Any] | None = None,
    prompt_template: str | None = None,
    generate_final_synthesis_answer_fn: Callable[..., str] = generate_final_synthesis_answer,
    extract_citation_indices_fn: Callable[[str], list[int]] = _extract_citation_indices,
    build_initial_answer_timeout_fallback_fn: Callable[[list[SubQuestionAnswer]], str] = _build_initial_answer_timeout_fallback,
    truncate_query_fn: Callable[[str], str] = _truncate_query,
) -> SynthesizeFinalNodeOutput:
    logger.info(
        "Final synthesis node start main_question=%s sub_qa_count=%s artifact_count=%s run_id=%s trace_id=%s correlation_id=%s",
        truncate_query_fn(node_input.main_question),
        len(node_input.sub_qa),
        len(node_input.sub_question_artifacts),
        node_input.run_metadata.run_id,
        node_input.run_metadata.trace_id,
        node_input.run_metadata.correlation_id,
    )
    generated_final_answer = generate_final_synthesis_answer_fn(
        main_question=node_input.main_question,
        sub_qa=node_input.sub_qa,
        prompt_template=prompt_template,
        callbacks=callbacks,
    )
    final_answer = _enforce_final_synthesis_citation_contract(
        generated_final_answer=generated_final_answer,
        sub_qa=node_input.sub_qa,
        sub_question_artifacts=node_input.sub_question_artifacts,
        run_id=node_input.run_metadata.run_id,
        extract_citation_indices_fn=extract_citation_indices_fn,
        build_initial_answer_timeout_fallback_fn=build_initial_answer_timeout_fallback_fn,
    )
    logger.info(
        "Final synthesis node complete output_len=%s run_id=%s",
        len(final_answer),
        node_input.run_metadata.run_id,
    )
    return SynthesizeFinalNodeOutput(final_answer=final_answer)


__all__ = ["run_synthesize_node"]
