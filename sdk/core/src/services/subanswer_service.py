from __future__ import annotations

import logging
import os
import re
from typing import Any

from langchain_openai import ChatOpenAI

from services.document_validation_service import RetrievedDocument, parse_retrieved_documents

logger = logging.getLogger(__name__)

_SUBANSWER_MODEL = os.getenv("SUBANSWER_MODEL", "gpt-4.1-mini")
_SUBANSWER_TEMPERATURE = float(os.getenv("SUBANSWER_TEMPERATURE", "0"))
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
_CITATION_PATTERN = re.compile(r"\[\d+\]")


def _build_context_block(documents: list[RetrievedDocument]) -> str:
    lines: list[str] = []
    for doc in documents:
        lines.append(
            f"[{doc.rank}] title={doc.title} source={doc.source} content={doc.content}"
        )
    return "\n".join(lines)


def _build_fallback_subanswer(*, sub_question: str, documents: list[RetrievedDocument]) -> str:
    if not documents:
        return "No relevant evidence found in reranked documents."
    top_doc = documents[0]
    return f"{top_doc.content} (source: {top_doc.source})"


def generate_subanswer(
    *,
    sub_question: str,
    reranked_retrieved_output: str,
    callbacks: list[Any] | None = None,
) -> str:
    documents = parse_retrieved_documents(reranked_retrieved_output)
    logger.info(
        "Subanswer generation parsed reranked docs sub_question=%s doc_count=%s",
        sub_question,
        len(documents),
    )
    if not documents:
        logger.info(
            "Subanswer generation skipped; no parseable reranked docs sub_question=%s",
            sub_question,
        )
        return _build_fallback_subanswer(sub_question=sub_question, documents=documents)

    context_block = _build_context_block(documents)
    fallback_answer = _build_fallback_subanswer(sub_question=sub_question, documents=documents)
    logger.info(
        "Subanswer generation context prepared sub_question=%s context_lines=%s",
        sub_question,
        len(context_block.splitlines()) if context_block else 0,
    )

    if not _OPENAI_API_KEY:
        logger.info(
            "Subanswer generation using fallback; OPENAI_API_KEY is not set sub_question=%s",
            sub_question,
        )
        return fallback_answer

    try:
        llm = ChatOpenAI(model=_SUBANSWER_MODEL, temperature=_SUBANSWER_TEMPERATURE)
        prompt = (
            "You answer one sub-question using the full reranked evidence list below.\n"
            "Requirements:\n"
            "- Use only the evidence provided below.\n"
            "- Treat each evidence line index as a citation key and cite claims with [index], e.g. [1] or [2][3].\n"
            "- Keep citation indices from the provided evidence lines; do not invent new indices.\n"
            "- Keep it to 1-3 sentences.\n"
            "- Do not summarize the evidence list; directly answer the sub-question using cited evidence.\n"
            "- If evidence is insufficient, explicitly say so.\n\n"
            f"Sub-question:\n{sub_question}\n\n"
            f"Reranked evidence:\n{context_block}\n"
        )
        invoke_config = {"callbacks": callbacks} if callbacks else None
        response = llm.invoke(prompt, config=invoke_config) if invoke_config else llm.invoke(prompt)
        answer = (response.content or "").strip() if hasattr(response, "content") else ""
        if answer:
            logger.info(
                "Subanswer generation LLM success sub_question=%s answer_len=%s citation_refs=%s",
                sub_question,
                len(answer),
                len(_CITATION_PATTERN.findall(answer)),
            )
            return answer
        logger.warning(
            "Subanswer generation returned empty LLM response; using fallback sub_question=%s",
            sub_question,
        )
    except Exception:
        logger.exception(
            "Subanswer generation LLM call failed; using fallback sub_question=%s model=%s",
            sub_question,
            _SUBANSWER_MODEL,
        )

    return fallback_answer
