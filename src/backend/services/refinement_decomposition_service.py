from __future__ import annotations

import json
import logging
import os
from typing import Any

from langchain_openai import ChatOpenAI

from schemas import SubQuestionAnswer

logger = logging.getLogger(__name__)

_REFINEMENT_DECOMPOSITION_MODEL = os.getenv("REFINEMENT_DECOMPOSITION_MODEL", "gpt-4.1-mini")
_REFINEMENT_DECOMPOSITION_TEMPERATURE = float(os.getenv("REFINEMENT_DECOMPOSITION_TEMPERATURE", "0"))
_REFINEMENT_DECOMPOSITION_MAX_SUBQUESTIONS = max(1, int(os.getenv("REFINEMENT_DECOMPOSITION_MAX_SUBQUESTIONS", "6")))
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()


def _normalize_question(text: str) -> str:
    normalized = (text or "").strip()
    if not normalized:
        return ""
    normalized = normalized.rstrip("?.! ").strip()
    if not normalized:
        return ""
    return f"{normalized}?"


def _format_sub_qa(sub_qa: list[SubQuestionAnswer]) -> str:
    lines: list[str] = []
    for index, item in enumerate(sub_qa, start=1):
        lines.append(
            "\n".join(
                [
                    f"[{index}] sub_question={item.sub_question}",
                    f"answerable={item.answerable}",
                    f"verification_reason={item.verification_reason}",
                    f"sub_answer={item.sub_answer}",
                ]
            )
        )
    return "\n\n".join(lines)


def _sanitize_refined_subquestions(
    *,
    candidates: list[str],
    existing_subquestions: list[str],
) -> list[str]:
    existing_normalized = {
        _normalize_question(question).lower()
        for question in existing_subquestions
        if _normalize_question(question)
    }
    output: list[str] = []
    seen: set[str] = set()

    for candidate in candidates:
        normalized = _normalize_question(candidate)
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in existing_normalized or lowered in seen:
            continue
        output.append(normalized)
        seen.add(lowered)
        if len(output) >= _REFINEMENT_DECOMPOSITION_MAX_SUBQUESTIONS:
            break
    return output


def _extract_llm_subquestions(content: Any) -> list[str]:
    if isinstance(content, list):
        return [str(item).strip() for item in content if str(item).strip()]

    text = str(content or "").strip()
    if not text:
        return []

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass

    lines = [line.strip("-* \t") for line in text.splitlines() if line.strip()]
    return [line for line in lines if line]


def _fallback_refined_subquestions(
    *,
    question: str,
    initial_answer: str,
    sub_qa: list[SubQuestionAnswer],
) -> list[str]:
    _ = initial_answer
    unresolved = [item for item in sub_qa if not item.answerable]
    candidates: list[str] = []

    for item in unresolved:
        normalized_subq = _normalize_question(item.sub_question)
        if not normalized_subq:
            continue
        candidates.append(f"What specific missing evidence is needed to answer {normalized_subq.rstrip('?')}?")
        if item.verification_reason:
            reason = item.verification_reason.replace("_", " ").strip()
            candidates.append(f"What sources can resolve this issue: {reason}?")

    if not candidates:
        candidates.append(
            f"What additional evidence is needed to fully answer {_normalize_question(question).rstrip('?')}?"
        )

    return _sanitize_refined_subquestions(
        candidates=candidates,
        existing_subquestions=[item.sub_question for item in sub_qa],
    )


def refine_subquestions(
    *,
    question: str,
    initial_answer: str,
    sub_qa: list[SubQuestionAnswer],
    callbacks: list[Any] | None = None,
) -> list[str]:
    logger.info(
        "Refinement decomposition start question_len=%s initial_answer_len=%s sub_qa_count=%s",
        len(question),
        len(initial_answer),
        len(sub_qa),
    )

    if not _OPENAI_API_KEY:
        fallback = _fallback_refined_subquestions(
            question=question,
            initial_answer=initial_answer,
            sub_qa=sub_qa,
        )
        logger.info(
            "Refinement decomposition complete via fallback count=%s",
            len(fallback),
        )
        return fallback

    prompt = (
        "You generate refined sub-questions for a retrieval pipeline.\n"
        "Goal: target gaps in the initial answer and unresolved sub-questions.\n\n"
        "Rules:\n"
        "- Output only refined sub-questions.\n"
        "- Do not repeat existing sub-questions.\n"
        "- Each output must be a complete question ending with '?'.\n"
        "- Keep each sub-question narrow and specific.\n"
        f"- Return at most {_REFINEMENT_DECOMPOSITION_MAX_SUBQUESTIONS} questions.\n"
        "- Return valid JSON as an array of strings.\n\n"
        f"User question:\n{question}\n\n"
        f"Initial answer:\n{initial_answer}\n\n"
        f"Existing sub-question results:\n{_format_sub_qa(sub_qa) or 'None'}\n"
    )

    try:
        llm = ChatOpenAI(
            model=_REFINEMENT_DECOMPOSITION_MODEL,
            temperature=_REFINEMENT_DECOMPOSITION_TEMPERATURE,
        )
        invoke_config = {"callbacks": callbacks} if callbacks else None
        response = llm.invoke(prompt, config=invoke_config) if invoke_config else llm.invoke(prompt)
        raw_candidates = _extract_llm_subquestions(getattr(response, "content", ""))
        refined = _sanitize_refined_subquestions(
            candidates=raw_candidates,
            existing_subquestions=[item.sub_question for item in sub_qa],
        )
        if refined:
            logger.info(
                "Refinement decomposition complete via LLM count=%s model=%s",
                len(refined),
                _REFINEMENT_DECOMPOSITION_MODEL,
            )
            return refined
        logger.warning("Refinement decomposition returned no valid LLM sub-questions; using fallback")
    except Exception:
        logger.exception(
            "Refinement decomposition LLM call failed; using fallback model=%s",
            _REFINEMENT_DECOMPOSITION_MODEL,
        )

    fallback = _fallback_refined_subquestions(
        question=question,
        initial_answer=initial_answer,
        sub_qa=sub_qa,
    )
    logger.info(
        "Refinement decomposition complete via fallback count=%s",
        len(fallback),
    )
    return fallback
