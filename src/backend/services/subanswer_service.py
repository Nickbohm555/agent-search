from __future__ import annotations

import logging
import os

from langchain_openai import ChatOpenAI

from services.document_validation_service import RetrievedDocument, parse_retrieved_documents

logger = logging.getLogger(__name__)

_SUBANSWER_MODEL = os.getenv("SUBANSWER_MODEL", "gpt-4.1-mini")
_SUBANSWER_TEMPERATURE = float(os.getenv("SUBANSWER_TEMPERATURE", "0"))
_SUBANSWER_MAX_CONTEXT_DOCS = max(1, int(os.getenv("SUBANSWER_MAX_CONTEXT_DOCS", "3")))
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()


def _build_context_block(documents: list[RetrievedDocument]) -> str:
    lines: list[str] = []
    for index, doc in enumerate(documents[:_SUBANSWER_MAX_CONTEXT_DOCS], start=1):
        lines.append(
            f"[{index}] title={doc.title} source={doc.source} content={doc.content}"
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
) -> str:
    documents = parse_retrieved_documents(reranked_retrieved_output)
    if not documents:
        logger.info(
            "Subanswer generation skipped; no parseable reranked docs sub_question=%s",
            sub_question,
        )
        return _build_fallback_subanswer(sub_question=sub_question, documents=documents)

    context_block = _build_context_block(documents)
    fallback_answer = _build_fallback_subanswer(sub_question=sub_question, documents=documents)

    if not _OPENAI_API_KEY:
        logger.info(
            "Subanswer generation using fallback; OPENAI_API_KEY is not set sub_question=%s",
            sub_question,
        )
        return fallback_answer

    try:
        llm = ChatOpenAI(model=_SUBANSWER_MODEL, temperature=_SUBANSWER_TEMPERATURE)
        prompt = (
            "You generate a concise answer for one sub-question from provided reranked evidence.\n"
            "Requirements:\n"
            "- Use only the evidence provided below.\n"
            "- Keep it to 1-3 sentences.\n"
            "- Include at least one source attribution in parentheses, e.g. (source: ...).\n"
            "- If evidence is insufficient, explicitly say so.\n\n"
            f"Sub-question:\n{sub_question}\n\n"
            f"Reranked evidence:\n{context_block}\n"
        )
        response = llm.invoke(prompt)
        answer = (response.content or "").strip() if hasattr(response, "content") else ""
        if answer:
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
