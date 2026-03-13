from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from schemas import DecomposeNodeInput, DecomposeNodeOutput
from schemas.decomposition import DecompositionPlan

logger = logging.getLogger(__name__)

_QUERY_LOG_MAX = 200
_DECOMPOSITION_ONLY_MODEL = os.getenv("DECOMPOSITION_ONLY_MODEL", os.getenv("RUNTIME_AGENT_MODEL", "gpt-4.1-mini"))
_DECOMPOSITION_ONLY_TEMPERATURE = float(os.getenv("DECOMPOSITION_ONLY_TEMPERATURE", "0"))
_DECOMPOSITION_ONLY_MAX_SUBQUESTIONS_RAW = os.getenv("DECOMPOSITION_ONLY_MAX_SUBQUESTIONS", "8")
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
_DECOMPOSITION_ONLY_PROMPT = (
    "You are a decomposition planner for retrieval.\n"
    "Task: break the user question into narrow, atomic sub-questions using the provided retrieval context.\n\n"
    "Rules:\n"
    "- Output only sub-questions; do not answer them.\n"
    "- One concept or entity per sub-question.\n"
    "- Every sub-question must end with '?'.\n"
    "- Prefer entities and concepts from the provided context.\n"
    "- Return valid JSON as an array of strings.\n"
)


def _coerce_decomposition_max_subquestions(raw_value: str) -> int:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        parsed = 8
    return min(10, max(5, parsed))


_DECOMPOSITION_ONLY_MAX_SUBQUESTIONS = _coerce_decomposition_max_subquestions(
    _DECOMPOSITION_ONLY_MAX_SUBQUESTIONS_RAW
)


def _truncate_query(q: str) -> str:
    return q[: _QUERY_LOG_MAX] + "..." if len(q) > _QUERY_LOG_MAX else q


def _normalize_sub_question(text: str) -> str:
    normalized = (text or "").strip()
    if not normalized:
        return ""
    normalized = normalized.rstrip("?.! ").strip()
    if not normalized:
        return ""
    return f"{normalized}?"


def _parse_decomposition_output(*, raw_output: Any, query: str) -> list[str]:
    fallback_question = _normalize_sub_question(query) or "What is the main question?"
    candidates: list[str] = []

    def _extend_candidates_from_json(value: Any) -> bool:
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    candidates.append(item.strip())
            return True
        if isinstance(value, dict):
            for key in ("sub_questions", "subquestions", "questions"):
                nested = value.get(key)
                if isinstance(nested, list):
                    for item in nested:
                        if isinstance(item, str) and item.strip():
                            candidates.append(item.strip())
                    return True
        return False

    if isinstance(raw_output, DecompositionPlan):
        candidates = list(raw_output.sub_questions or [])
    elif isinstance(raw_output, list):
        for item in raw_output:
            if isinstance(item, str) and item.strip():
                candidates.append(item.strip())
        if not candidates:
            logger.warning("Decomposition output empty; using fallback question")
            return [fallback_question]
    else:
        text = str(raw_output or "").strip()
        if not text:
            logger.warning("Decomposition output empty; using fallback question")
            return [fallback_question]

        parsed_json: Any | None = None
        json_parse_attempted = False
        try:
            json_parse_attempted = True
            parsed = json.loads(text)
            parsed_json = parsed
            _extend_candidates_from_json(parsed)
        except json.JSONDecodeError:
            pass

        if not candidates and not (
            json_parse_attempted and parsed_json is not None and isinstance(parsed_json, (dict, list))
        ):
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            bullet_prefix = re.compile(r"^(?:[-*]|\d+[.)])\s*")
            for line in lines:
                line = bullet_prefix.sub("", line).strip()
                line = line.strip("\"'")
                if line:
                    candidates.append(line)

    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        sub_question = _normalize_sub_question(candidate)
        if not sub_question:
            continue
        lowered = sub_question.lower()
        if lowered in seen:
            continue
        normalized.append(sub_question)
        seen.add(lowered)

    if normalized:
        if len(normalized) > _DECOMPOSITION_ONLY_MAX_SUBQUESTIONS:
            logger.info(
                "Decomposition output truncated count=%s max=%s",
                len(normalized),
                _DECOMPOSITION_ONLY_MAX_SUBQUESTIONS,
            )
            normalized = normalized[:_DECOMPOSITION_ONLY_MAX_SUBQUESTIONS]
        if len(normalized) < 5:
            logger.info(
                "Decomposition output below target_min count=%s target_min=%s",
                len(normalized),
                5,
            )
        return normalized

    logger.warning("Decomposition output malformed; using fallback question")
    return [fallback_question]


def _build_decomposition_only_input_message(query: str, initial_search_context: list[dict[str, Any]]) -> str:
    serialized_context = json.dumps(initial_search_context, ensure_ascii=True)
    return (
        f"User question:\n{query}\n\n"
        "Initial retrieval context:\n"
        f"{serialized_context}\n"
    )


def _run_decomposition_only_llm_call(
    *,
    query: str,
    initial_search_context: list[dict[str, Any]],
    model: BaseChatModel | None = None,
    callbacks: list[Any] | None = None,
) -> list[str]:
    fallback_question = _normalize_sub_question(query) or f"{query.strip()}?"
    if model is None and not _OPENAI_API_KEY:
        logger.info(
            "Decomposition-only LLM call using fallback; OPENAI_API_KEY is not set model=%s",
            _DECOMPOSITION_ONLY_MODEL,
        )
        return [fallback_question]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _DECOMPOSITION_ONLY_PROMPT),
            ("human", "{input_message}"),
        ]
    )
    try:
        llm = model or ChatOpenAI(
            model=_DECOMPOSITION_ONLY_MODEL,
            temperature=_DECOMPOSITION_ONLY_TEMPERATURE,
        )
        logger.info(
            "Decomposition-only LLM call model selection provided_model=%s default_model=%s",
            model is not None,
            _DECOMPOSITION_ONLY_MODEL,
        )
        chain = prompt | llm.with_structured_output(DecompositionPlan)
        invoke_config = {"callbacks": callbacks} if callbacks else None
        if invoke_config:
            result = chain.invoke(
                {"input_message": _build_decomposition_only_input_message(query, initial_search_context)},
                config=invoke_config,
            )
        else:
            result = chain.invoke(
                {"input_message": _build_decomposition_only_input_message(query, initial_search_context)}
            )
        if isinstance(result, DecompositionPlan) and result.sub_questions:
            return result.sub_questions
        logger.warning(
            "Decomposition-only LLM call returned empty content; using fallback model=%s",
            _DECOMPOSITION_ONLY_MODEL,
        )
    except Exception:
        logger.exception(
            "Decomposition-only LLM call failed; using fallback model=%s",
            _DECOMPOSITION_ONLY_MODEL,
        )
    return [fallback_question]


def run_decomposition_node(
    *,
    node_input: DecomposeNodeInput,
    model: BaseChatModel | None = None,
    timeout_s: int | None = None,
    callbacks: list[Any] | None = None,
    run_llm_call_fn: Callable[..., list[str]] = _run_decomposition_only_llm_call,
    parse_output_fn: Callable[..., list[str]] = _parse_decomposition_output,
    normalize_sub_question_fn: Callable[[str], str] = _normalize_sub_question,
    truncate_query_fn: Callable[[str], str] = _truncate_query,
) -> DecomposeNodeOutput:
    _ = timeout_s
    logger.info(
        "Decomposition node start query=%s context_docs=%s run_id=%s trace_id=%s correlation_id=%s",
        truncate_query_fn(node_input.main_question),
        len(node_input.initial_search_context),
        node_input.run_metadata.run_id,
        node_input.run_metadata.trace_id,
        node_input.run_metadata.correlation_id,
    )
    decomposition_raw_output = run_llm_call_fn(
        query=node_input.main_question,
        initial_search_context=node_input.initial_search_context,
        model=model,
        callbacks=callbacks,
    )

    decomposition_raw_output_preview = json.dumps(decomposition_raw_output, ensure_ascii=True)
    logger.info(
        "Decomposition-only LLM output captured output_length=%s output_preview=%s",
        len(decomposition_raw_output),
        truncate_query_fn(decomposition_raw_output_preview),
    )
    decomposition_sub_questions = parse_output_fn(
        raw_output=decomposition_raw_output,
        query=node_input.main_question,
    )
    logger.info(
        "Decomposition output parsed sub_question_count=%s sub_questions=%s run_id=%s",
        len(decomposition_sub_questions),
        json.dumps(decomposition_sub_questions, ensure_ascii=True),
        node_input.run_metadata.run_id,
    )
    return DecomposeNodeOutput(decomposition_sub_questions=decomposition_sub_questions)


__all__ = ["run_decomposition_node"]
