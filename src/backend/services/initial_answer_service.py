from __future__ import annotations

import logging
import os
import re
from typing import Any

from langchain_openai import ChatOpenAI

from schemas import SubQuestionAnswer

logger = logging.getLogger(__name__)

_INITIAL_ANSWER_MODEL = os.getenv("INITIAL_ANSWER_MODEL", "gpt-4.1-mini")
_INITIAL_ANSWER_TEMPERATURE = float(os.getenv("INITIAL_ANSWER_TEMPERATURE", "0"))
_INITIAL_ANSWER_MAX_CONTEXT_ITEMS = max(1, int(os.getenv("INITIAL_ANSWER_MAX_CONTEXT_ITEMS", "4")))
_INITIAL_ANSWER_MAX_SUBQAS = max(1, int(os.getenv("INITIAL_ANSWER_MAX_SUBQAS", "8")))
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
_CITATION_REF_PATTERN = re.compile(r"\[(\d+)\]")


def _format_initial_context(initial_search_context: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, item in enumerate(initial_search_context[:_INITIAL_ANSWER_MAX_CONTEXT_ITEMS], start=1):
        title = str(item.get("title", "")).strip() or "Untitled"
        source = str(item.get("source", "")).strip() or "unknown"
        snippet = str(item.get("snippet", "")).strip() or "No snippet provided."
        lines.append(f"[{index}] title={title} source={source} snippet={snippet}")
    return "\n".join(lines)


def _format_sub_qa(sub_qa: list[SubQuestionAnswer]) -> str:
    lines: list[str] = []
    for index, item in enumerate(sub_qa[:_INITIAL_ANSWER_MAX_SUBQAS], start=1):
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


def _count_citation_refs(text: str) -> int:
    return len(_CITATION_REF_PATTERN.findall(text or ""))


def _build_fallback_initial_answer(
    *,
    main_question: str,
    initial_search_context: list[dict[str, Any]],
    sub_qa: list[SubQuestionAnswer],
) -> str:
    answerable_subanswers = [item.sub_answer.strip() for item in sub_qa if item.answerable and item.sub_answer.strip()]
    if answerable_subanswers:
        logger.info(
            "Initial answer fallback path selected source=answerable_subanswers count=%s citation_refs=%s",
            len(answerable_subanswers),
            sum(_count_citation_refs(answer) for answer in answerable_subanswers),
        )
        return " ".join(answerable_subanswers[:2])

    any_subanswers = [item.sub_answer.strip() for item in sub_qa if item.sub_answer.strip()]
    if any_subanswers:
        logger.info(
            "Initial answer fallback path selected source=any_subanswers count=%s citation_refs=%s",
            len(any_subanswers),
            sum(_count_citation_refs(answer) for answer in any_subanswers),
        )
        return " ".join(any_subanswers[:2])

    if initial_search_context:
        top_item = initial_search_context[0]
        snippet = str(top_item.get("snippet", "")).strip()
        source = str(top_item.get("source", "")).strip() or "unknown source"
        if snippet:
            logger.info(
                "Initial answer fallback path selected source=initial_context top_source=%s",
                source,
            )
            return f"Based on initial retrieval, {snippet} (source: {source})."

    return (
        f"Insufficient evidence to provide an initial answer for '{main_question}'. "
        "No validated sub-question evidence was available."
    )


def generate_initial_answer(
    *,
    main_question: str,
    initial_search_context: list[dict[str, Any]],
    sub_qa: list[SubQuestionAnswer],
) -> str:
    logger.info(
        "Initial answer generation start question_len=%s context_items=%s sub_qa_count=%s",
        len(main_question),
        len(initial_search_context),
        len(sub_qa),
    )

    fallback_answer = _build_fallback_initial_answer(
        main_question=main_question,
        initial_search_context=initial_search_context,
        sub_qa=sub_qa,
    )
    answerable_count = sum(1 for item in sub_qa if item.answerable)
    subanswer_citation_refs = sum(_count_citation_refs(item.sub_answer) for item in sub_qa)
    logger.info(
        "Initial answer evidence prepared answerable_sub_qa=%s total_sub_qa=%s subanswer_citation_refs=%s context_sources=%s",
        answerable_count,
        len(sub_qa),
        subanswer_citation_refs,
        len(initial_search_context),
    )

    if not _OPENAI_API_KEY:
        logger.info("Initial answer generation using fallback; OPENAI_API_KEY is not set")
        return fallback_answer

    prompt = (
        "You synthesize the initial answer for the user's question.\n"
        "Use both sources of input:\n"
        "1) Initial retrieval context from the original question.\n"
        "2) Per-subquestion answers with verification status.\n\n"
        "Requirements:\n"
        "- Return a concise answer (2-5 sentences).\n"
        "- Prefer answerable/verified sub-question answers when present.\n"
        "- If evidence is partial, say what is uncertain.\n"
        "- Preserve citation markers from sub-question answers exactly, e.g. [1], [2][3].\n"
        "- Do not collapse cited evidence into an uncited summary.\n"
        "- Include at least one source attribution in parentheses, e.g. (source: ...).\n"
        "- If initial retrieval context is used, reference its source field explicitly.\n\n"
        f"Main question:\n{main_question}\n\n"
        f"Initial retrieval context:\n{_format_initial_context(initial_search_context) or 'None'}\n\n"
        f"Sub-question answers:\n{_format_sub_qa(sub_qa) or 'None'}\n"
    )

    try:
        llm = ChatOpenAI(model=_INITIAL_ANSWER_MODEL, temperature=_INITIAL_ANSWER_TEMPERATURE)
        response = llm.invoke(prompt)
        answer = (response.content or "").strip() if hasattr(response, "content") else ""
        if answer:
            logger.info(
                "Initial answer generation complete via LLM answer_len=%s model=%s citation_refs=%s source_attributions=%s",
                len(answer),
                _INITIAL_ANSWER_MODEL,
                _count_citation_refs(answer),
                answer.lower().count("(source:"),
            )
            return answer
        logger.warning("Initial answer generation returned empty LLM response; using fallback")
    except Exception:
        logger.exception(
            "Initial answer generation LLM call failed; using fallback model=%s",
            _INITIAL_ANSWER_MODEL,
        )

    return fallback_answer
