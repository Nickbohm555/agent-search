from __future__ import annotations

import ast
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError, as_completed, wait
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from agents import create_coordinator_agent, get_decomposition_only_prompt
from db import DATABASE_URL
from schemas import (
    AgentGraphState,
    AnswerSubquestionNodeInput,
    AnswerSubquestionNodeOutput,
    CitationSourceRow,
    DecomposeNodeInput,
    DecomposeNodeOutput,
    ExpandNodeInput,
    ExpandNodeOutput,
    GraphRunMetadata,
    RerankNodeInput,
    RerankNodeOutput,
    SearchNodeInput,
    SearchNodeOutput,
    RuntimeAgentRunRequest,
    RuntimeAgentRunResponse,
    SubQuestionAnswer,
    SubQuestionArtifacts,
)
from schemas.decomposition import DecompositionPlan
from services.document_validation_service import (
    RetrievedDocument,
    build_document_validation_config_from_env,
    format_retrieved_documents,
    parse_retrieved_documents,
    validate_subquestion_documents,
)
from services.reranker_service import build_reranker_config_from_env, rerank_documents
from services.initial_answer_service import generate_initial_answer
from services.query_expansion_service import (
    QueryExpansionConfig,
    build_query_expansion_config_from_env,
    expand_queries_for_subquestion,
)
from services.refinement_decomposition_service import refine_subquestions
from services.refinement_decision_service import should_refine
from services.subanswer_service import generate_subanswer
from services.subanswer_verification_service import (
    SubanswerVerificationResult,
    verify_subanswer,
)
from services.vector_store_service import (
    build_initial_search_context,
    get_vector_store,
    search_documents_for_queries,
    search_documents_for_context,
)
from utils.agent_callbacks import (
    AgentLoggingCallbackHandler,
    SearchDatabaseCaptureCallback,
    log_agent_messages_summary,
)
from utils.embeddings import get_embedding_model
from utils.langfuse_tracing import (
    build_langfuse_run_metadata,
    build_langfuse_callback_handler,
    flush_langfuse_callback_handler,
)

logger = logging.getLogger(__name__)

_VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")
_RUNTIME_AGENT_MODEL = os.getenv("RUNTIME_AGENT_MODEL", "gpt-4.1-mini")
_DECOMPOSITION_ONLY_MODEL = os.getenv("DECOMPOSITION_ONLY_MODEL", _RUNTIME_AGENT_MODEL)
_DECOMPOSITION_ONLY_TEMPERATURE = float(os.getenv("DECOMPOSITION_ONLY_TEMPERATURE", "0"))
_DECOMPOSITION_ONLY_MAX_SUBQUESTIONS_RAW = os.getenv("DECOMPOSITION_ONLY_MAX_SUBQUESTIONS", "8")
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
_MAIN_AGENT_TASK_TOOL_NAME = "task"
_SEARCH_DATABASE_TOOL_NAME = "search_database"
_VECTOR_STORE_TIMEOUT_FALLBACK_MESSAGE = (
    "Knowledge base retrieval is temporarily unavailable. Please try again in a moment."
)
_INITIAL_ANSWER_TIMEOUT_FALLBACK_PREFIX = "Answer generation timed out; partial context only."
_SUBANSWER_GENERATION_TIMEOUT_FALLBACK_TEXT = "Answer not available in time."
_SUBANSWER_VERIFICATION_TIMEOUT_FALLBACK_REASON = "verification_timed_out"
_SUBQUESTION_PIPELINE_TIMEOUT_FALLBACK_REASON = "subquestion_pipeline_timed_out"


_QUERY_LOG_MAX = 200
_INITIAL_SEARCH_CONTEXT_K = int(os.getenv("INITIAL_SEARCH_CONTEXT_K", "5"))
_INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD_RAW = os.getenv("INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD")
_INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD = (
    float(_INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD_RAW)
    if _INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD_RAW not in (None, "")
    else None
)
_DOCUMENT_VALIDATION_CONFIG = build_document_validation_config_from_env()
_RERANKER_CONFIG = build_reranker_config_from_env()
_QUERY_EXPANSION_CONFIG = build_query_expansion_config_from_env()
_SUBQUESTION_PIPELINE_MAX_WORKERS = int(os.getenv("SUBQUESTION_PIPELINE_MAX_WORKERS", "4"))
_REFINEMENT_RETRIEVAL_K = max(1, int(os.getenv("REFINEMENT_RETRIEVAL_K", "10")))
_SEARCH_NODE_K_FETCH = max(1, int(os.getenv("SEARCH_NODE_K_FETCH", "10")))
_ANSWER_SUBQUESTION_NO_SUPPORT_FALLBACK = "nothing relevant found"
_CITATION_INDEX_PATTERN = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class RuntimeTimeoutConfig:
    vector_store_acquisition_timeout_s: int
    initial_search_timeout_s: int
    decomposition_llm_timeout_s: int
    coordinator_invoke_timeout_s: int
    document_validation_timeout_s: int
    rerank_timeout_s: int
    subanswer_generation_timeout_s: int
    subanswer_verification_timeout_s: int
    subquestion_pipeline_total_timeout_s: int
    initial_answer_timeout_s: int
    refinement_decision_timeout_s: int
    refinement_decomposition_timeout_s: int
    refinement_retrieval_timeout_s: int
    refinement_pipeline_total_timeout_s: int
    refined_answer_timeout_s: int


def _read_timeout_seconds(env_key: str, default: int) -> int:
    raw_value = os.getenv(env_key, "").strip()
    if not raw_value:
        return default
    try:
        parsed = int(raw_value)
    except ValueError:
        logger.warning(
            "Invalid timeout env value; using default env_key=%s value=%s default=%s",
            env_key,
            raw_value,
            default,
        )
        return default
    if parsed <= 0:
        logger.warning(
            "Non-positive timeout env value; using default env_key=%s value=%s default=%s",
            env_key,
            parsed,
            default,
        )
        return default
    return parsed


def build_runtime_timeout_config_from_env() -> RuntimeTimeoutConfig:
    return RuntimeTimeoutConfig(
        vector_store_acquisition_timeout_s=_read_timeout_seconds("VECTOR_STORE_ACQUISITION_TIMEOUT_S", 20),
        initial_search_timeout_s=_read_timeout_seconds("INITIAL_SEARCH_TIMEOUT_S", 20),
        decomposition_llm_timeout_s=_read_timeout_seconds("DECOMPOSITION_LLM_TIMEOUT_S", 60),
        coordinator_invoke_timeout_s=_read_timeout_seconds("COORDINATOR_INVOKE_TIMEOUT_S", 90),
        document_validation_timeout_s=_read_timeout_seconds("DOCUMENT_VALIDATION_TIMEOUT_S", 20),
        rerank_timeout_s=_read_timeout_seconds("RERANK_TIMEOUT_S", 20),
        subanswer_generation_timeout_s=_read_timeout_seconds("SUBANSWER_GENERATION_TIMEOUT_S", 60),
        subanswer_verification_timeout_s=_read_timeout_seconds("SUBANSWER_VERIFICATION_TIMEOUT_S", 30),
        subquestion_pipeline_total_timeout_s=_read_timeout_seconds("SUBQUESTION_PIPELINE_TOTAL_TIMEOUT_S", 120),
        initial_answer_timeout_s=_read_timeout_seconds("INITIAL_ANSWER_TIMEOUT_S", 60),
        refinement_decision_timeout_s=_read_timeout_seconds("REFINEMENT_DECISION_TIMEOUT_S", 30),
        refinement_decomposition_timeout_s=_read_timeout_seconds("REFINEMENT_DECOMPOSITION_TIMEOUT_S", 60),
        refinement_retrieval_timeout_s=_read_timeout_seconds("REFINEMENT_RETRIEVAL_TIMEOUT_S", 30),
        refinement_pipeline_total_timeout_s=_read_timeout_seconds("REFINEMENT_PIPELINE_TOTAL_TIMEOUT_S", 120),
        refined_answer_timeout_s=_read_timeout_seconds("REFINED_ANSWER_TIMEOUT_S", 60),
    )


_RUNTIME_TIMEOUT_CONFIG = build_runtime_timeout_config_from_env()


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


def _normalize_sub_qa_questions(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]:
    for item in sub_qa:
        normalized = _normalize_sub_question(item.sub_question)
        if normalized and normalized != item.sub_question:
            logger.info(
                "Normalized sub_question original=%s normalized=%s",
                _truncate_query(item.sub_question),
                _truncate_query(normalized),
            )
            item.sub_question = normalized
    return sub_qa


def _estimate_retrieved_doc_count(search_output: str) -> int:
    if not isinstance(search_output, str) or not search_output.strip():
        return 0
    return len(re.findall(r"^\d+\.\s", search_output, flags=re.MULTILINE))


def _estimate_citation_contract_line_count(search_output: str) -> int:
    if not isinstance(search_output, str) or not search_output.strip():
        return 0
    return len(
        re.findall(
            r"^\d+\.\s+title=.*?\s+source=.*?\s+content=.*$",
            search_output,
            flags=re.MULTILINE,
        )
    )


def _format_retrieved_documents_for_pipeline(documents: list[Any]) -> str:
    if not documents:
        return "No relevant documents found."

    normalized_documents: list[RetrievedDocument] = []
    for index, result in enumerate(documents, start=1):
        metadata = result.metadata if hasattr(result, "metadata") and isinstance(result.metadata, dict) else {}
        title = str(metadata.get("title") or metadata.get("wiki_page") or "Unknown title")
        source = str(metadata.get("source") or metadata.get("wiki_url") or "Unknown source")
        content = str(getattr(result, "page_content", "")).strip()
        normalized_documents.append(
            RetrievedDocument(
                rank=index,
                title=title,
                source=source,
                content=content,
            )
        )
    formatted = format_retrieved_documents(normalized_documents)
    logger.info(
        "Pipeline retrieval formatter emitted citation contract document_count=%s contract_lines=%s contract=%s",
        len(normalized_documents),
        _estimate_citation_contract_line_count(formatted),
        "index.title.source.content",
    )
    return formatted


def _stringify_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return str(content)


def _run_with_timeout(*, timeout_s: int, operation_name: str, fn: Any) -> Any:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        return future.result(timeout=timeout_s)
    except FuturesTimeoutError:
        future.cancel()
        logger.warning(
            "Runtime guardrail timeout operation=%s timeout_s=%s",
            operation_name,
            timeout_s,
        )
        raise
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def _build_coordinator_input_message(decomposition_sub_questions: list[str]) -> str:
    serialized_subquestions = json.dumps(decomposition_sub_questions, ensure_ascii=True)
    return (
        "Provided sub-questions for delegation:\n"
        f"{serialized_subquestions}\n\n"
        "Delegation requirements:\n"
        "- These sub-questions are already decomposed and normalized.\n"
        "- Delegate each provided sub-question via task(description=<exact sub-question>).\n"
        "- Preserve the provided order and trailing '?'.\n"
        "- Do not create new decomposition sub-questions unless refinement is explicitly required later."
    )


def _build_fallback_sub_qa_from_decomposition(decomposition_sub_questions: list[str]) -> list[SubQuestionAnswer]:
    fallback_sub_qa: list[SubQuestionAnswer] = []
    for item in decomposition_sub_questions:
        normalized = _normalize_sub_question(item)
        if not normalized:
            continue
        fallback_sub_qa.append(
            SubQuestionAnswer(
                sub_question=normalized,
                sub_answer="No relevant documents found.",
                tool_call_input="{}",
                expanded_query="",
                sub_agent_response="",
            )
        )
    logger.info(
        "Coordinator timeout fallback sub_qa seeded from decomposition count=%s",
        len(fallback_sub_qa),
    )
    return fallback_sub_qa


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
            ("system", get_decomposition_only_prompt()),
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


def _is_main_agent_turn(msg: AIMessage) -> bool:
    tool_calls = getattr(msg, "tool_calls", None)
    if not isinstance(tool_calls, list):
        return False
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        if tool_call.get("name") == _MAIN_AGENT_TASK_TOOL_NAME:
            return True
    return False


def _extract_last_message_content(result: Any) -> str:
    messages = result.get("messages") if isinstance(result, dict) else None
    if not isinstance(messages, list) or not messages:
        raise ValueError("Agent invoke result missing non-empty messages list.")

    last_message = messages[-1]
    content = getattr(last_message, "content", None)
    if isinstance(content, str):
        return content
    if content is None:
        raise ValueError("Agent invoke result last message content is empty.")
    return str(content)


def _get_description_from_args(args: Any) -> str:
    """Extract a single display string from task/description args (e.g. description key)."""
    if isinstance(args, dict):
        for key in ("description", "sub_question", "question", "query", "input"):
            value = args.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return str(args)
    if isinstance(args, str):
        return args.strip()
    return str(args) if args is not None else ""


def _tool_results_by_call_id(messages: list[BaseMessage]) -> dict[str, str]:
    out: dict[str, str] = {}
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        tool_call_id = getattr(msg, "tool_call_id", None)
        if not isinstance(tool_call_id, str) or not tool_call_id:
            continue
        content = getattr(msg, "content", "")
        out[tool_call_id] = _stringify_message_content(content)
    return out


def _task_items_ordered(messages: list[BaseMessage]) -> list[tuple[str, str, str]]:
    """Return (tool_call_id, description, tool_call_input_json) for each main-agent 'task' call, in order."""
    items: list[tuple[str, str, str]] = []
    for msg in messages:
        if not isinstance(msg, AIMessage) or not _is_main_agent_turn(msg):
            continue
        tool_calls = getattr(msg, "tool_calls", None)
        if not isinstance(tool_calls, list):
            continue
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict) or tool_call.get("name") != _MAIN_AGENT_TASK_TOOL_NAME:
                continue
            tool_call_id = tool_call.get("id")
            if not isinstance(tool_call_id, str) or not tool_call_id:
                continue
            args = tool_call.get("args")
            desc = _get_description_from_args(args)
            tool_call_input = json.dumps(args) if isinstance(args, dict) else str(args) if args is not None else "{}"
            if desc:
                items.append((tool_call_id, desc, tool_call_input))
    return items


def _parse_tool_input_for_query(input_str: str) -> str:
    """Parse search_database tool input string to get the query for sub_question display."""
    if not input_str or not isinstance(input_str, str):
        return ""
    s = input_str.strip()
    if not s:
        return ""
    if s.startswith("{"):
        try:
            data = json.loads(s)
            if isinstance(data, dict):
                return _get_description_from_args(data)
        except json.JSONDecodeError:
            pass
        try:
            data = ast.literal_eval(s)
            if isinstance(data, dict):
                return _get_description_from_args(data)
        except (ValueError, SyntaxError):
            pass
    return s


def _parse_tool_input_for_expanded_query(input_str: str) -> str:
    if not input_str or not isinstance(input_str, str):
        return ""
    s = input_str.strip()
    if not s or not s.startswith("{"):
        return ""
    try:
        data = json.loads(s)
        if isinstance(data, dict):
            value = data.get("expanded_query")
            if isinstance(value, str):
                return value.strip()
    except json.JSONDecodeError:
        pass
    try:
        data = ast.literal_eval(s)
        if isinstance(data, dict):
            value = data.get("expanded_query")
            if isinstance(value, str):
                return value.strip()
    except (ValueError, SyntaxError):
        pass
    return ""


def _extract_sub_qa(
    messages: list[BaseMessage],
    search_database_calls: list[tuple[str, str]] | None = None,
) -> list[SubQuestionAnswer]:
    # Prefer callback-captured search_database calls so UI shows retriever input/output.
    # sub_agent_response = subagent's final answer (task ToolMessage content); sub_answer = raw retrieval.
    if search_database_calls:
        tool_results_by_call_id = _tool_results_by_call_id(messages)
        task_items_ordered = _task_items_ordered(messages)
        task_final_answers = [
            tool_results_by_call_id.get(tid) or ""
            for (tid, _, _) in task_items_ordered
        ]
        sub_qa = []
        for i, (input_str, output_str) in enumerate(search_database_calls):
            sub_question = _parse_tool_input_for_query(input_str) or "Search"
            expanded_query = _parse_tool_input_for_expanded_query(input_str)
            sub_agent_response = task_final_answers[i] if i < len(task_final_answers) else ""
            retrieved_doc_count = _estimate_retrieved_doc_count(output_str)
            sub_qa.append(
                SubQuestionAnswer(
                    sub_question=sub_question,
                    sub_answer=output_str,
                    tool_call_input=input_str if isinstance(input_str, str) else str(input_str),
                    expanded_query=expanded_query,
                    sub_agent_response=sub_agent_response,
                )
            )
            logger.info(
                "Per-subquestion search result sub_question=%s expanded_query=%s docs_retrieved=%s sub_agent_response_len=%s",
                _truncate_query(sub_question),
                _truncate_query(expanded_query),
                retrieved_doc_count,
                len(sub_agent_response),
            )
        sub_qa = _normalize_sub_qa_questions(sub_qa)
        logger.info("Extracted sub_qa from search_database callback count=%s", len(sub_qa))
        return sub_qa

    tool_results_by_call_id: dict[str, str] = {}
    tool_message_indices_by_call_id: dict[str, int] = {}
    for i, msg in enumerate(messages):
        if not isinstance(msg, ToolMessage):
            continue
        tool_call_id = getattr(msg, "tool_call_id", None)
        if not isinstance(tool_call_id, str) or not tool_call_id:
            continue
        content = getattr(msg, "content", "")
        content_str = _stringify_message_content(content)
        tool_results_by_call_id[tool_call_id] = content_str
        tool_message_indices_by_call_id[tool_call_id] = i

    # Main agent delegates via "task" tool; collect (tool_call_id, description) for pairing with task results.
    task_items: list[tuple[str, str, str]] = []  # (tool_call_id, description, tool_call_input_json)
    for msg in messages:
        if not isinstance(msg, AIMessage) or not _is_main_agent_turn(msg):
            continue
        tool_calls = getattr(msg, "tool_calls", None)
        if not isinstance(tool_calls, list):
            continue
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict) or tool_call.get("name") != _MAIN_AGENT_TASK_TOOL_NAME:
                continue
            tool_call_id = tool_call.get("id")
            if not isinstance(tool_call_id, str) or not tool_call_id:
                continue
            args = tool_call.get("args")
            desc = _get_description_from_args(args)
            tool_call_input = json.dumps(args) if isinstance(args, dict) else str(args) if args is not None else "{}"
            if desc:
                task_items.append((tool_call_id, desc, tool_call_input))

    # Collect search_database tool calls from any agent (main or subagent). The coordinator's
    # subagent holds the retriever tool, so these calls appear on subagent AIMessages, not main.
    search_db_items: list[tuple[str, str, str, int]] = []
    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        tool_calls = getattr(msg, "tool_calls", None)
        if not isinstance(tool_calls, list):
            continue
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict) or tool_call.get("name") != _SEARCH_DATABASE_TOOL_NAME:
                continue
            tool_call_id = tool_call.get("id")
            if not isinstance(tool_call_id, str) or not tool_call_id:
                continue
            args = tool_call.get("args")
            tool_call_input = json.dumps(args) if isinstance(args, dict) else str(args) if args is not None else "{}"
            sub_answer = tool_results_by_call_id.get(tool_call_id)
            if sub_answer is None:
                continue
            tool_message_index = tool_message_indices_by_call_id.get(tool_call_id, -1)
            search_db_items.append((tool_call_id, tool_call_input, sub_answer, tool_message_index))

    task_descriptions = [t[1] for t in task_items]

    sub_qa: list[SubQuestionAnswer] = []
    if search_db_items:
        # Subagent search_database calls are in the message list; use them.
        for idx, (tool_call_id, tool_call_input, sub_answer, tool_message_index) in enumerate(search_db_items):
            if idx < len(task_descriptions):
                sub_question = task_descriptions[idx]
            else:
                try:
                    args = json.loads(tool_call_input) if isinstance(tool_call_input, str) and tool_call_input.strip().startswith("{") else None
                except (json.JSONDecodeError, TypeError):
                    args = None
                sub_question = _get_description_from_args(args)
            sub_qa.append(
                SubQuestionAnswer(
                    sub_question=sub_question,
                    sub_answer=sub_answer,
                    tool_call_input=tool_call_input,
                    expanded_query=_parse_tool_input_for_expanded_query(tool_call_input),
                )
            )
            logger.info(
                "Extracted sub_qa item tool_call_id=%s sub_question=%s tool_call_input=%s",
                tool_call_id,
                _truncate_query(sub_question),
                _truncate_query(tool_call_input),
            )

        for idx, (tool_call_id, _input, _answer, tool_message_index) in enumerate(search_db_items):
            if idx >= len(sub_qa):
                break
            if tool_message_index < 0:
                continue
            last_sub_agent_response = ""
            for later_msg in messages[tool_message_index + 1 :]:
                if not isinstance(later_msg, AIMessage):
                    continue
                if _is_main_agent_turn(later_msg):
                    break
                content_str = _stringify_message_content(getattr(later_msg, "content", ""))
                if content_str.strip():
                    last_sub_agent_response = content_str
            sub_qa[idx].sub_agent_response = last_sub_agent_response
            logger.info(
                "Extracted sub_agent_response tool_call_id=%s response_preview=%s",
                tool_call_id,
                _truncate_query(last_sub_agent_response),
            )
    else:
        # Subagent messages are not in top-level messages (e.g. deep agent isolates subagent run).
        # Build sub_qa from main agent "task" tool calls and their ToolMessage results.
        for task_call_id, desc, tool_call_input in task_items:
            sub_answer = tool_results_by_call_id.get(task_call_id)
            if sub_answer is None:
                continue
            sub_qa.append(
                SubQuestionAnswer(
                    sub_question=desc,
                    sub_answer=sub_answer,
                    tool_call_input=tool_call_input,
                    expanded_query=_parse_tool_input_for_expanded_query(tool_call_input),
                    sub_agent_response="",
                )
            )
            logger.info(
                "Extracted sub_qa from task tool_call_id=%s sub_question=%s",
                task_call_id,
                _truncate_query(desc),
            )

    sub_qa = _normalize_sub_qa_questions(sub_qa)
    logger.info("Extracted sub_qa pairs count=%s", len(sub_qa))
    return sub_qa


def _log_sub_qa_run_end_summary(sub_qa: list[SubQuestionAnswer]) -> None:
    logger.info("SubQuestionAnswer summary count=%s", len(sub_qa))
    for index, item in enumerate(sub_qa, start=1):
        logger.info(
            "SubQuestionAnswer[%s] sub_question=%s expanded_query=%s tool_call_input=%s sub_answer=%s sub_agent_response=%s answerable=%s verification_reason=%s",
            index,
            _truncate_query(item.sub_question),
            _truncate_query(item.expanded_query),
            _truncate_query(item.tool_call_input),
            _truncate_query(item.sub_answer),
            _truncate_query(item.sub_agent_response),
            item.answerable,
            _truncate_query(item.verification_reason),
        )


def _apply_document_validation_to_sub_qa(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]:
    logger.info(
        "Per-subquestion document validation start count=%s min_relevance_score=%s source_allowlist_count=%s min_year=%s max_year=%s max_workers=%s",
        len(sub_qa),
        _DOCUMENT_VALIDATION_CONFIG.min_relevance_score,
        len(_DOCUMENT_VALIDATION_CONFIG.source_allowlist),
        _DOCUMENT_VALIDATION_CONFIG.min_year,
        _DOCUMENT_VALIDATION_CONFIG.max_year,
        _DOCUMENT_VALIDATION_CONFIG.max_workers,
    )
    for item in sub_qa:
        validation_result = validate_subquestion_documents(
            sub_question=item.sub_question,
            retrieved_output=item.sub_answer,
            config=_DOCUMENT_VALIDATION_CONFIG,
        )
        if validation_result.total_documents > 0:
            item.sub_answer = format_retrieved_documents(validation_result.valid_documents)
        else:
            logger.info(
                "Per-subquestion document validation skipped; no parseable retrieved docs sub_question=%s",
                _truncate_query(item.sub_question),
            )
        logger.info(
            "Per-subquestion document validation sub_question=%s docs_before=%s docs_after=%s rejected=%s contract_lines=%s",
            _truncate_query(item.sub_question),
            validation_result.total_documents,
            len(validation_result.valid_documents) if validation_result.total_documents > 0 else "n/a",
            (
                validation_result.total_documents - len(validation_result.valid_documents)
                if validation_result.total_documents > 0
                else "n/a"
            ),
            _estimate_citation_contract_line_count(item.sub_answer),
        )
    return sub_qa


def _apply_reranking_to_sub_qa(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]:
    logger.info(
        "Per-subquestion reranking start count=%s enabled=%s top_n=%s model_name=%s",
        len(sub_qa),
        _RERANKER_CONFIG.enabled,
        _RERANKER_CONFIG.top_n,
        _RERANKER_CONFIG.model_name,
    )
    for item in sub_qa:
        parsed_documents = parse_retrieved_documents(item.sub_answer)
        if not parsed_documents:
            logger.info(
                "Per-subquestion reranking skipped; no parseable retrieved docs sub_question=%s",
                _truncate_query(item.sub_question),
            )
            continue

        rerank_query = item.expanded_query.strip() or item.sub_question
        reranked = rerank_documents(
            query=rerank_query,
            documents=parsed_documents,
            config=_RERANKER_CONFIG,
        )
        reranked_documents = [entry.document for entry in reranked]
        item.sub_answer = format_retrieved_documents(reranked_documents)
        logger.info(
            "Per-subquestion reranking sub_question=%s query=%s docs_before=%s docs_after=%s top_document=%s contract_lines=%s",
            _truncate_query(item.sub_question),
            _truncate_query(rerank_query),
            len(parsed_documents),
            len(reranked_documents),
            _truncate_query(reranked_documents[0].title if reranked_documents else "n/a"),
            _estimate_citation_contract_line_count(item.sub_answer),
        )
    return sub_qa


def _apply_subanswer_generation_to_sub_qa(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]:
    logger.info("Per-subquestion subanswer generation start count=%s", len(sub_qa))
    for item in sub_qa:
        prior_output = item.sub_answer
        item.sub_answer = generate_subanswer(
            sub_question=item.sub_question,
            reranked_retrieved_output=prior_output,
        )
        logger.info(
            "Per-subquestion subanswer generated sub_question=%s generated_len=%s",
            _truncate_query(item.sub_question),
            len(item.sub_answer),
        )
    return sub_qa


def _apply_subanswer_verification_to_sub_qa(
    sub_qa: list[SubQuestionAnswer],
    *,
    reranked_output_by_sub_question: dict[str, str],
) -> list[SubQuestionAnswer]:
    logger.info("Per-subquestion subanswer verification start count=%s", len(sub_qa))
    for item in sub_qa:
        verification = verify_subanswer(
            sub_question=item.sub_question,
            sub_answer=item.sub_answer,
            reranked_retrieved_output=reranked_output_by_sub_question.get(item.sub_question, ""),
        )
        item.answerable = verification.answerable
        item.verification_reason = verification.reason
        logger.info(
            "Per-subquestion subanswer verification sub_question=%s answerable=%s reason=%s",
            _truncate_query(item.sub_question),
            item.answerable,
            _truncate_query(item.verification_reason),
        )
    return sub_qa


def _run_pipeline_for_single_subquestion(item: SubQuestionAnswer) -> SubQuestionAnswer:
    working_item = item.model_copy(deep=True)
    logger.info(
        "Per-subquestion pipeline item start sub_question=%s",
        _truncate_query(working_item.sub_question),
    )
    try:
        working_item = _run_with_timeout(
            timeout_s=_RUNTIME_TIMEOUT_CONFIG.document_validation_timeout_s,
            operation_name="document_validation_subquestion",
            fn=lambda: _apply_document_validation_to_sub_qa([working_item])[0],
        )
    except FuturesTimeoutError:
        logger.warning(
            "Per-subquestion document validation timeout; continuing without validation sub_question=%s timeout_s=%s",
            _truncate_query(working_item.sub_question),
            _RUNTIME_TIMEOUT_CONFIG.document_validation_timeout_s,
        )
    try:
        working_item = _run_with_timeout(
            timeout_s=_RUNTIME_TIMEOUT_CONFIG.rerank_timeout_s,
            operation_name="rerank_subquestion",
            fn=lambda: _apply_reranking_to_sub_qa([working_item])[0],
        )
    except FuturesTimeoutError:
        logger.warning(
            "Per-subquestion reranking timeout; continuing with original document order sub_question=%s timeout_s=%s",
            _truncate_query(working_item.sub_question),
            _RUNTIME_TIMEOUT_CONFIG.rerank_timeout_s,
        )
    reranked_output = working_item.sub_answer
    try:
        working_item = _run_with_timeout(
            timeout_s=_RUNTIME_TIMEOUT_CONFIG.subanswer_generation_timeout_s,
            operation_name="subanswer_generation_subquestion",
            fn=lambda: _apply_subanswer_generation_to_sub_qa([working_item])[0],
        )
    except FuturesTimeoutError:
        working_item.sub_answer = _SUBANSWER_GENERATION_TIMEOUT_FALLBACK_TEXT
        logger.warning(
            "Per-subquestion subanswer generation timeout; continuing with fallback text sub_question=%s timeout_s=%s",
            _truncate_query(working_item.sub_question),
            _RUNTIME_TIMEOUT_CONFIG.subanswer_generation_timeout_s,
        )
    try:
        working_item = _run_with_timeout(
            timeout_s=_RUNTIME_TIMEOUT_CONFIG.subanswer_verification_timeout_s,
            operation_name="subanswer_verification_subquestion",
            fn=lambda: _apply_subanswer_verification_to_sub_qa(
                [working_item],
                reranked_output_by_sub_question={working_item.sub_question: reranked_output},
            )[0],
        )
    except FuturesTimeoutError:
        working_item.answerable = False
        working_item.verification_reason = _SUBANSWER_VERIFICATION_TIMEOUT_FALLBACK_REASON
        logger.warning(
            "Per-subquestion subanswer verification timeout; continuing with default unanswerable status sub_question=%s timeout_s=%s",
            _truncate_query(working_item.sub_question),
            _RUNTIME_TIMEOUT_CONFIG.subanswer_verification_timeout_s,
        )
    logger.info(
        "Per-subquestion pipeline item complete sub_question=%s answerable=%s reason=%s",
        _truncate_query(working_item.sub_question),
        working_item.answerable,
        _truncate_query(working_item.verification_reason),
    )
    return working_item


def run_pipeline_for_subquestions(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]:
    return run_pipeline_for_subquestions_with_timeout(sub_qa=sub_qa, total_timeout_s=None)


def _build_subquestion_pipeline_timeout_fallback(item: SubQuestionAnswer) -> SubQuestionAnswer:
    fallback_item = item.model_copy(deep=True)
    fallback_item.answerable = False
    fallback_item.verification_reason = _SUBQUESTION_PIPELINE_TIMEOUT_FALLBACK_REASON
    return fallback_item


def _build_initial_answer_timeout_fallback(sub_qa: list[SubQuestionAnswer]) -> str:
    partial_answers = [item.sub_answer.strip() for item in sub_qa if isinstance(item.sub_answer, str) and item.sub_answer.strip()]
    if not partial_answers:
        return _INITIAL_ANSWER_TIMEOUT_FALLBACK_PREFIX
    joined = " ".join(partial_answers)
    return f"{_INITIAL_ANSWER_TIMEOUT_FALLBACK_PREFIX} {joined}"


def build_graph_run_metadata(
    *,
    run_id: str | None = None,
    thread_id: str | None = None,
    trace_id: str | None = None,
    correlation_id: str | None = None,
) -> GraphRunMetadata:
    metadata = build_langfuse_run_metadata(
        run_id=run_id,
        thread_id=thread_id,
        trace_id=trace_id,
        correlation_id=correlation_id,
    )
    return GraphRunMetadata(**metadata)


def _build_citation_source_row(*, citation_index: int, rank: int, item: SubQuestionAnswer) -> CitationSourceRow:
    return CitationSourceRow(
        citation_index=citation_index,
        rank=rank,
        title="",
        source="",
        content=item.sub_answer,
        document_id="",
        score=None,
    )


def _build_subquestion_artifact_from_subqa(item: SubQuestionAnswer, rank: int) -> SubQuestionArtifacts:
    expanded_queries = [item.expanded_query] if isinstance(item.expanded_query, str) and item.expanded_query.strip() else []
    citation_rows_by_index = {
        rank: _build_citation_source_row(citation_index=rank, rank=rank, item=item),
    }
    return SubQuestionArtifacts(
        sub_question=item.sub_question,
        expanded_queries=expanded_queries,
        retrieved_docs=[],
        reranked_docs=[],
        sub_answer=item.sub_answer,
        citation_rows_by_index=citation_rows_by_index,
    )


def build_agent_graph_state(
    *,
    main_question: str,
    decomposition_sub_questions: list[str] | None = None,
    sub_qa: list[SubQuestionAnswer] | None = None,
    final_answer: str = "",
    run_metadata: GraphRunMetadata | None = None,
) -> AgentGraphState:
    normalized_sub_qa = [item.model_copy(deep=True) for item in (sub_qa or [])]
    artifacts = [
        _build_subquestion_artifact_from_subqa(item, rank=index)
        for index, item in enumerate(normalized_sub_qa, start=1)
    ]
    citation_rows_by_index: dict[int, CitationSourceRow] = {}
    for artifact in artifacts:
        citation_rows_by_index.update(artifact.citation_rows_by_index)

    resolved_decomposition = decomposition_sub_questions or [item.sub_question for item in normalized_sub_qa]
    resolved_metadata = run_metadata or build_graph_run_metadata()
    resolved_output = final_answer.strip()
    state = AgentGraphState(
        main_question=main_question,
        decomposition_sub_questions=list(resolved_decomposition),
        sub_question_artifacts=artifacts,
        final_answer=resolved_output,
        citation_rows_by_index=citation_rows_by_index,
        run_metadata=resolved_metadata,
        sub_qa=normalized_sub_qa,
        output=resolved_output,
    )
    logger.info(
        "Agent graph state built main_question_len=%s decomposition_count=%s artifact_count=%s sub_qa_count=%s run_id=%s trace_id=%s correlation_id=%s",
        len(main_question),
        len(state.decomposition_sub_questions),
        len(state.sub_question_artifacts),
        len(state.sub_qa),
        state.run_metadata.run_id,
        state.run_metadata.trace_id,
        state.run_metadata.correlation_id,
    )
    return state


def map_graph_state_to_runtime_response(state: AgentGraphState) -> RuntimeAgentRunResponse:
    output = state.output.strip() or state.final_answer
    response = RuntimeAgentRunResponse(
        main_question=state.main_question,
        sub_qa=[item.model_copy(deep=True) for item in state.sub_qa],
        output=output,
    )
    logger.info(
        "Agent graph state mapped to runtime response sub_qa_count=%s output_len=%s run_id=%s",
        len(response.sub_qa),
        len(response.output),
        state.run_metadata.run_id,
    )
    return response


def _select_compat_expanded_query(*, sub_question: str, expanded_queries: list[str]) -> str:
    for query in expanded_queries:
        if query.strip() and query.casefold() != sub_question.casefold():
            return query
    return ""


def _normalize_search_queries(*, sub_question: str, expanded_queries: list[str]) -> list[str]:
    candidates = [sub_question, *expanded_queries]
    normalized: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        query = (candidate or "").strip()
        if not query:
            continue
        lowered = query.casefold()
        if lowered in seen:
            continue
        normalized.append(query)
        seen.add(lowered)
    return normalized


def _build_document_identity(
    *,
    document_id: str,
    source: str,
    content: str,
) -> str:
    if document_id:
        return f"document_id:{document_id}"
    normalized_source = source.strip().casefold()
    normalized_content = content.strip()
    return f"source_content:{normalized_source}|{normalized_content}"


def _build_citation_row_from_document(*, document: Any, rank: int) -> CitationSourceRow:
    metadata = document.metadata or {}
    title = str(metadata.get("topic") or metadata.get("title") or metadata.get("wiki_page") or "").strip()
    source = str(metadata.get("wiki_url") or metadata.get("source") or "").strip()
    content = str(getattr(document, "page_content", "") or "").strip()
    document_id = str(getattr(document, "id", "") or "").strip()
    return CitationSourceRow(
        citation_index=rank,
        rank=rank,
        title=title,
        source=source,
        content=content,
        document_id=document_id,
        score=None,
    )


def _format_citation_rows_for_pipeline(rows: list[CitationSourceRow]) -> str:
    documents = [
        RetrievedDocument(
            rank=row.rank,
            title=row.title,
            source=row.source,
            content=row.content,
        )
        for row in rows
    ]
    return format_retrieved_documents(documents)


def _to_retrieved_documents(rows: list[CitationSourceRow]) -> list[RetrievedDocument]:
    return [
        RetrievedDocument(
            rank=row.rank,
            title=row.title,
            source=row.source,
            content=row.content,
        )
        for row in rows
    ]


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


def apply_expand_node_output_to_graph_state(
    *,
    state: AgentGraphState,
    sub_question: str,
    node_output: ExpandNodeOutput,
) -> AgentGraphState:
    next_state = state.model_copy(deep=True)
    artifact = next(
        (item for item in next_state.sub_question_artifacts if item.sub_question == sub_question),
        None,
    )
    if artifact is None:
        artifact = SubQuestionArtifacts(sub_question=sub_question)
        next_state.sub_question_artifacts.append(artifact)
    artifact.expanded_queries = list(node_output.expanded_queries)

    compat_expanded_query = _select_compat_expanded_query(
        sub_question=sub_question,
        expanded_queries=node_output.expanded_queries,
    )
    for item in next_state.sub_qa:
        if item.sub_question == sub_question:
            item.expanded_query = compat_expanded_query
            break

    logger.info(
        "Expansion node state update sub_question=%s expanded_query_count=%s compat_expanded_query=%s run_id=%s",
        _truncate_query(sub_question),
        len(node_output.expanded_queries),
        _truncate_query(compat_expanded_query),
        next_state.run_metadata.run_id,
    )
    return next_state


def run_search_node(
    *,
    node_input: SearchNodeInput,
    vector_store: Any,
    k_fetch: int | None = None,
) -> SearchNodeOutput:
    effective_k_fetch = max(1, k_fetch or _SEARCH_NODE_K_FETCH)
    normalized_queries = _normalize_search_queries(
        sub_question=node_input.sub_question,
        expanded_queries=node_input.expanded_queries,
    )
    logger.info(
        "Search node start sub_question=%s expanded_query_count=%s normalized_query_count=%s k_fetch=%s run_id=%s trace_id=%s correlation_id=%s",
        _truncate_query(node_input.sub_question),
        len(node_input.expanded_queries),
        len(normalized_queries),
        effective_k_fetch,
        node_input.run_metadata.run_id,
        node_input.run_metadata.trace_id,
        node_input.run_metadata.correlation_id,
    )
    if not normalized_queries:
        logger.warning(
            "Search node skipped; no valid queries sub_question=%s run_id=%s",
            _truncate_query(node_input.sub_question),
            node_input.run_metadata.run_id,
        )
        return SearchNodeOutput()

    documents_by_query = search_documents_for_queries(
        vector_store=vector_store,
        queries=normalized_queries,
        k=effective_k_fetch,
        score_threshold=None,
    )
    merged_rows: list[CitationSourceRow] = []
    retrieval_provenance: list[dict[str, Any]] = []
    seen_document_identities: set[str] = set()

    for query_index, query in enumerate(normalized_queries, start=1):
        docs_for_query = documents_by_query.get(query, [])
        for query_rank, document in enumerate(docs_for_query, start=1):
            row = _build_citation_row_from_document(document=document, rank=len(merged_rows) + 1)
            document_identity = _build_document_identity(
                document_id=row.document_id,
                source=row.source,
                content=row.content,
            )
            retrieval_provenance.append(
                {
                    "query": query,
                    "query_index": query_index,
                    "query_rank": query_rank,
                    "document_identity": document_identity,
                    "document_id": row.document_id,
                    "source": row.source,
                    "deduped": document_identity in seen_document_identities,
                }
            )
            if document_identity in seen_document_identities:
                continue
            seen_document_identities.add(document_identity)
            row.rank = len(merged_rows) + 1
            row.citation_index = len(merged_rows) + 1
            merged_rows.append(row)

    citation_rows_by_index = {item.citation_index: item for item in merged_rows}
    logger.info(
        "Search node complete sub_question=%s query_count=%s raw_candidates=%s merged_candidates=%s run_id=%s",
        _truncate_query(node_input.sub_question),
        len(normalized_queries),
        sum(len(documents_by_query.get(query, [])) for query in normalized_queries),
        len(merged_rows),
        node_input.run_metadata.run_id,
    )
    return SearchNodeOutput(
        retrieved_docs=merged_rows,
        retrieval_provenance=retrieval_provenance,
        citation_rows_by_index=citation_rows_by_index,
    )


def apply_search_node_output_to_graph_state(
    *,
    state: AgentGraphState,
    sub_question: str,
    node_output: SearchNodeOutput,
) -> AgentGraphState:
    next_state = state.model_copy(deep=True)
    artifact = next(
        (item for item in next_state.sub_question_artifacts if item.sub_question == sub_question),
        None,
    )
    if artifact is None:
        artifact = SubQuestionArtifacts(sub_question=sub_question)
        next_state.sub_question_artifacts.append(artifact)
    artifact.retrieved_docs = [row.model_copy(deep=True) for row in node_output.retrieved_docs]
    artifact.retrieval_provenance = list(node_output.retrieval_provenance)
    artifact.citation_rows_by_index = {
        key: value.model_copy(deep=True)
        for key, value in node_output.citation_rows_by_index.items()
    }

    for index, row in node_output.citation_rows_by_index.items():
        next_state.citation_rows_by_index[index] = row.model_copy(deep=True)

    retrieved_output = _format_citation_rows_for_pipeline(node_output.retrieved_docs)
    compat_input_payload = {
        "query": sub_question,
        "expanded_queries": list(artifact.expanded_queries),
        "retrieval_provenance": list(node_output.retrieval_provenance),
        "limit": len(node_output.retrieved_docs),
    }
    matched_sub_qa = None
    for item in next_state.sub_qa:
        if item.sub_question == sub_question:
            matched_sub_qa = item
            break
    if matched_sub_qa is None:
        matched_sub_qa = SubQuestionAnswer(sub_question=sub_question, sub_answer="")
        next_state.sub_qa.append(matched_sub_qa)

    matched_sub_qa.sub_answer = retrieved_output
    matched_sub_qa.tool_call_input = json.dumps(compat_input_payload, ensure_ascii=True)
    matched_sub_qa.expanded_query = _select_compat_expanded_query(
        sub_question=sub_question,
        expanded_queries=artifact.expanded_queries,
    )

    logger.info(
        "Search node state update sub_question=%s merged_candidates=%s provenance_events=%s run_id=%s",
        _truncate_query(sub_question),
        len(node_output.retrieved_docs),
        len(node_output.retrieval_provenance),
        next_state.run_metadata.run_id,
    )
    return next_state


def run_rerank_node(
    *,
    node_input: RerankNodeInput,
    config: Any | None = None,
) -> RerankNodeOutput:
    effective_config = config or _RERANKER_CONFIG
    logger.info(
        "Rerank node start sub_question=%s candidate_count=%s enabled=%s top_n=%s model=%s run_id=%s trace_id=%s correlation_id=%s",
        _truncate_query(node_input.sub_question),
        len(node_input.retrieved_docs),
        effective_config.enabled,
        effective_config.top_n,
        effective_config.model_name,
        node_input.run_metadata.run_id,
        node_input.run_metadata.trace_id,
        node_input.run_metadata.correlation_id,
    )
    if not node_input.retrieved_docs:
        logger.info(
            "Rerank node skipped; no retrieved candidates sub_question=%s run_id=%s",
            _truncate_query(node_input.sub_question),
            node_input.run_metadata.run_id,
        )
        return RerankNodeOutput()

    original_by_rank = {row.rank: row for row in node_input.retrieved_docs}
    reranked_scores = rerank_documents(
        query=node_input.sub_question,
        documents=_to_retrieved_documents(node_input.retrieved_docs),
        config=effective_config,
    )

    reranked_docs: list[CitationSourceRow] = []
    for new_rank, reranked in enumerate(reranked_scores, start=1):
        original_row = original_by_rank.get(reranked.original_rank)
        reranked_docs.append(
            CitationSourceRow(
                citation_index=new_rank,
                rank=new_rank,
                title=reranked.document.title,
                source=reranked.document.source,
                content=reranked.document.content,
                document_id=original_row.document_id if original_row is not None else "",
                score=reranked.score,
            )
        )

    citation_rows_by_index = {row.citation_index: row for row in reranked_docs}
    logger.info(
        "Rerank node complete sub_question=%s candidates_before=%s candidates_after=%s run_id=%s",
        _truncate_query(node_input.sub_question),
        len(node_input.retrieved_docs),
        len(reranked_docs),
        node_input.run_metadata.run_id,
    )
    return RerankNodeOutput(
        reranked_docs=reranked_docs,
        citation_rows_by_index=citation_rows_by_index,
    )


def apply_rerank_node_output_to_graph_state(
    *,
    state: AgentGraphState,
    sub_question: str,
    node_output: RerankNodeOutput,
) -> AgentGraphState:
    next_state = state.model_copy(deep=True)
    artifact = next(
        (item for item in next_state.sub_question_artifacts if item.sub_question == sub_question),
        None,
    )
    if artifact is None:
        artifact = SubQuestionArtifacts(sub_question=sub_question)
        next_state.sub_question_artifacts.append(artifact)
    artifact.reranked_docs = [row.model_copy(deep=True) for row in node_output.reranked_docs]
    artifact.citation_rows_by_index = {
        key: value.model_copy(deep=True)
        for key, value in node_output.citation_rows_by_index.items()
    }
    for index, row in node_output.citation_rows_by_index.items():
        next_state.citation_rows_by_index[index] = row.model_copy(deep=True)

    reranked_output = _format_citation_rows_for_pipeline(node_output.reranked_docs)
    rerank_provenance = [
        {
            "reranked_rank": row.rank,
            "citation_index": row.citation_index,
            "score": row.score,
            "document_id": row.document_id,
            "source": row.source,
        }
        for row in node_output.reranked_docs
    ]
    matched_sub_qa = None
    for item in next_state.sub_qa:
        if item.sub_question == sub_question:
            matched_sub_qa = item
            break
    if matched_sub_qa is None:
        matched_sub_qa = SubQuestionAnswer(sub_question=sub_question, sub_answer="")
        next_state.sub_qa.append(matched_sub_qa)
    matched_sub_qa.sub_answer = reranked_output

    tool_call_payload: dict[str, Any] = {}
    if matched_sub_qa.tool_call_input:
        try:
            parsed_tool_payload = json.loads(matched_sub_qa.tool_call_input)
            if isinstance(parsed_tool_payload, dict):
                tool_call_payload = parsed_tool_payload
        except json.JSONDecodeError:
            tool_call_payload = {}
    tool_call_payload["rerank_provenance"] = rerank_provenance
    tool_call_payload["rerank_top_n"] = len(node_output.reranked_docs)
    matched_sub_qa.tool_call_input = json.dumps(tool_call_payload, ensure_ascii=True)

    logger.info(
        "Rerank node state update sub_question=%s reranked_candidates=%s run_id=%s",
        _truncate_query(sub_question),
        len(node_output.reranked_docs),
        next_state.run_metadata.run_id,
    )
    return next_state


def run_answer_subquestion_node(
    *,
    node_input: AnswerSubquestionNodeInput,
) -> AnswerSubquestionNodeOutput:
    logger.info(
        "Subanswer node start sub_question=%s reranked_doc_count=%s run_id=%s trace_id=%s correlation_id=%s",
        _truncate_query(node_input.sub_question),
        len(node_input.reranked_docs),
        node_input.run_metadata.run_id,
        node_input.run_metadata.trace_id,
        node_input.run_metadata.correlation_id,
    )

    if not node_input.reranked_docs:
        logger.info(
            "Subanswer node fallback; no reranked docs sub_question=%s run_id=%s",
            _truncate_query(node_input.sub_question),
            node_input.run_metadata.run_id,
        )
        return AnswerSubquestionNodeOutput(
            sub_answer=_ANSWER_SUBQUESTION_NO_SUPPORT_FALLBACK,
            citation_indices_used=[],
            answerable=False,
            verification_reason="no_reranked_documents",
            citation_rows_by_index={},
        )

    reranked_output = _format_citation_rows_for_pipeline(node_input.reranked_docs)
    generated_sub_answer = generate_subanswer(
        sub_question=node_input.sub_question,
        reranked_retrieved_output=reranked_output,
    )
    verification = verify_subanswer(
        sub_question=node_input.sub_question,
        sub_answer=generated_sub_answer,
        reranked_retrieved_output=reranked_output,
    )

    citation_rows = dict(node_input.citation_rows_by_index)
    if not citation_rows:
        citation_rows = {row.citation_index: row for row in node_input.reranked_docs}
    citation_indices_used = _extract_citation_indices(generated_sub_answer)
    supports_answer = bool(verification.answerable)
    invalid_indices = [index for index in citation_indices_used if index not in citation_rows]
    missing_citations = supports_answer and not citation_indices_used
    missing_support_rows = supports_answer and bool(citation_indices_used) and bool(invalid_indices)

    if missing_citations:
        supports_answer = False
        verification = SubanswerVerificationResult(
            answerable=False,
            reason="missing_citation_markers",
        )
    elif missing_support_rows:
        supports_answer = False
        verification = SubanswerVerificationResult(
            answerable=False,
            reason="missing_supporting_source_rows",
        )

    if not supports_answer:
        logger.info(
            "Subanswer node fallback; unsupported answer sub_question=%s reason=%s citation_indices=%s run_id=%s",
            _truncate_query(node_input.sub_question),
            verification.reason,
            citation_indices_used,
            node_input.run_metadata.run_id,
        )
        return AnswerSubquestionNodeOutput(
            sub_answer=_ANSWER_SUBQUESTION_NO_SUPPORT_FALLBACK,
            citation_indices_used=[],
            answerable=False,
            verification_reason=verification.reason,
            citation_rows_by_index={},
        )

    supporting_rows = {
        index: citation_rows[index].model_copy(deep=True)
        for index in citation_indices_used
        if index in citation_rows
    }
    logger.info(
        "Subanswer node complete sub_question=%s answer_len=%s citation_count=%s run_id=%s",
        _truncate_query(node_input.sub_question),
        len(generated_sub_answer),
        len(citation_indices_used),
        node_input.run_metadata.run_id,
    )
    return AnswerSubquestionNodeOutput(
        sub_answer=generated_sub_answer,
        citation_indices_used=citation_indices_used,
        answerable=True,
        verification_reason=verification.reason,
        citation_rows_by_index=supporting_rows,
    )


def apply_answer_subquestion_node_output_to_graph_state(
    *,
    state: AgentGraphState,
    sub_question: str,
    node_output: AnswerSubquestionNodeOutput,
) -> AgentGraphState:
    next_state = state.model_copy(deep=True)
    artifact = next(
        (item for item in next_state.sub_question_artifacts if item.sub_question == sub_question),
        None,
    )
    if artifact is None:
        artifact = SubQuestionArtifacts(sub_question=sub_question)
        next_state.sub_question_artifacts.append(artifact)
    artifact.sub_answer = node_output.sub_answer
    artifact.citation_rows_by_index = {
        key: value.model_copy(deep=True)
        for key, value in node_output.citation_rows_by_index.items()
    }
    for index, row in node_output.citation_rows_by_index.items():
        next_state.citation_rows_by_index[index] = row.model_copy(deep=True)

    matched_sub_qa = None
    for item in next_state.sub_qa:
        if item.sub_question == sub_question:
            matched_sub_qa = item
            break
    if matched_sub_qa is None:
        matched_sub_qa = SubQuestionAnswer(sub_question=sub_question, sub_answer="")
        next_state.sub_qa.append(matched_sub_qa)

    matched_sub_qa.sub_answer = node_output.sub_answer
    matched_sub_qa.answerable = node_output.answerable
    matched_sub_qa.verification_reason = node_output.verification_reason

    tool_call_payload: dict[str, Any] = {}
    if matched_sub_qa.tool_call_input:
        try:
            parsed_tool_payload = json.loads(matched_sub_qa.tool_call_input)
            if isinstance(parsed_tool_payload, dict):
                tool_call_payload = parsed_tool_payload
        except json.JSONDecodeError:
            tool_call_payload = {}
    tool_call_payload["citation_usage"] = list(node_output.citation_indices_used)
    tool_call_payload["supporting_source_rows"] = [
        {
            "citation_index": row.citation_index,
            "rank": row.rank,
            "title": row.title,
            "source": row.source,
            "document_id": row.document_id,
            "score": row.score,
        }
        for row in node_output.citation_rows_by_index.values()
    ]
    matched_sub_qa.tool_call_input = json.dumps(tool_call_payload, ensure_ascii=True)

    logger.info(
        "Subanswer node state update sub_question=%s answerable=%s citation_count=%s run_id=%s",
        _truncate_query(sub_question),
        node_output.answerable,
        len(node_output.citation_indices_used),
        next_state.run_metadata.run_id,
    )
    return next_state


def run_decomposition_node(
    *,
    node_input: DecomposeNodeInput,
    model: BaseChatModel | None = None,
    timeout_s: int | None = None,
) -> DecomposeNodeOutput:
    effective_timeout_s = timeout_s or _RUNTIME_TIMEOUT_CONFIG.decomposition_llm_timeout_s
    logger.info(
        "Decomposition node start query=%s context_docs=%s timeout_s=%s run_id=%s trace_id=%s correlation_id=%s",
        _truncate_query(node_input.main_question),
        len(node_input.initial_search_context),
        effective_timeout_s,
        node_input.run_metadata.run_id,
        node_input.run_metadata.trace_id,
        node_input.run_metadata.correlation_id,
    )
    try:
        decomposition_raw_output = _run_with_timeout(
            timeout_s=effective_timeout_s,
            operation_name="decomposition_llm_call",
            fn=lambda: _run_decomposition_only_llm_call(
                query=node_input.main_question,
                initial_search_context=node_input.initial_search_context,
                model=model,
            ),
        )
    except FuturesTimeoutError:
        fallback_sub_question = _normalize_sub_question(node_input.main_question) or "What is the main question?"
        decomposition_raw_output = [fallback_sub_question]
        logger.warning(
            "Decomposition LLM timeout; continuing with fallback sub-question query=%s timeout_s=%s fallback=%s",
            _truncate_query(node_input.main_question),
            effective_timeout_s,
            _truncate_query(fallback_sub_question),
        )
    decomposition_raw_output_preview = json.dumps(decomposition_raw_output, ensure_ascii=True)
    logger.info(
        "Decomposition-only LLM output captured output_length=%s output_preview=%s",
        len(decomposition_raw_output),
        _truncate_query(decomposition_raw_output_preview),
    )
    decomposition_sub_questions = _parse_decomposition_output(
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


def run_expand_node(
    *,
    node_input: ExpandNodeInput,
    model: BaseChatModel | None = None,
    config: QueryExpansionConfig | None = None,
) -> ExpandNodeOutput:
    effective_config = config or _QUERY_EXPANSION_CONFIG
    logger.info(
        "Expansion node start sub_question=%s max_queries=%s max_query_length=%s run_id=%s trace_id=%s correlation_id=%s",
        _truncate_query(node_input.sub_question),
        effective_config.max_queries,
        effective_config.max_query_length,
        node_input.run_metadata.run_id,
        node_input.run_metadata.trace_id,
        node_input.run_metadata.correlation_id,
    )
    expanded_queries = expand_queries_for_subquestion(
        sub_question=node_input.sub_question,
        model=model,
        config=effective_config,
    )
    logger.info(
        "Expansion node complete sub_question=%s expanded_query_count=%s expanded_queries=%s run_id=%s",
        _truncate_query(node_input.sub_question),
        len(expanded_queries),
        json.dumps(expanded_queries, ensure_ascii=True),
        node_input.run_metadata.run_id,
    )
    return ExpandNodeOutput(expanded_queries=expanded_queries)


def run_pipeline_for_subquestions_with_timeout(
    *,
    sub_qa: list[SubQuestionAnswer],
    total_timeout_s: int | None,
) -> list[SubQuestionAnswer]:
    if not sub_qa:
        logger.info("Per-subquestion pipeline skipped; no sub-questions")
        return []

    configured_workers = max(1, _SUBQUESTION_PIPELINE_MAX_WORKERS)
    max_workers = min(configured_workers, len(sub_qa))
    logger.info(
        "Per-subquestion pipeline parallel start count=%s configured_max_workers=%s effective_workers=%s",
        len(sub_qa),
        configured_workers,
        max_workers,
    )
    output: list[SubQuestionAnswer | None] = [None] * len(sub_qa)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_run_pipeline_for_single_subquestion, item): index
            for index, item in enumerate(sub_qa)
        }

        if total_timeout_s is None:
            for future in as_completed(futures):
                index = futures[future]
                output[index] = future.result()
        else:
            done, pending = wait(set(futures.keys()), timeout=total_timeout_s)
            for future in done:
                index = futures[future]
                output[index] = future.result()
            if pending:
                for future in pending:
                    future.cancel()
                for future in pending:
                    index = futures[future]
                    output[index] = _build_subquestion_pipeline_timeout_fallback(sub_qa[index])
                logger.warning(
                    "Per-subquestion pipeline total timeout; returning partial results completed=%s skipped=%s timeout_s=%s",
                    len(done),
                    len(pending),
                    total_timeout_s,
                )

    processed = [item for item in output if item is not None]
    logger.info(
        "Per-subquestion pipeline parallel complete count=%s timeout_s=%s",
        len(processed),
        total_timeout_s,
    )
    return processed


def _seed_refined_sub_qa_from_retrieval(
    *,
    vector_store: Any,
    refined_subquestions: list[str],
) -> list[SubQuestionAnswer]:
    if not refined_subquestions:
        logger.info("Refinement retrieval skipped; no refined sub-questions")
        return []

    configured_workers = max(1, _SUBQUESTION_PIPELINE_MAX_WORKERS)
    max_workers = min(configured_workers, len(refined_subquestions))
    logger.info(
        "Refinement retrieval start count=%s k=%s configured_max_workers=%s effective_workers=%s",
        len(refined_subquestions),
        _REFINEMENT_RETRIEVAL_K,
        configured_workers,
        max_workers,
    )

    output: list[SubQuestionAnswer | None] = [None] * len(refined_subquestions)

    def _retrieve(index_and_question: tuple[int, str]) -> tuple[int, SubQuestionAnswer]:
        index, sub_question = index_and_question
        documents = search_documents_for_context(
            vector_store=vector_store,
            query=sub_question,
            k=_REFINEMENT_RETRIEVAL_K,
            score_threshold=None,
        )
        retrieved_output = _format_retrieved_documents_for_pipeline(documents)
        docs_retrieved = len(documents)
        logger.info(
            "Refinement retrieval item sub_question=%s docs_retrieved=%s",
            _truncate_query(sub_question),
            docs_retrieved,
        )
        return (
            index,
            SubQuestionAnswer(
                sub_question=sub_question,
                sub_answer=retrieved_output,
                tool_call_input=json.dumps({"query": sub_question, "limit": _REFINEMENT_RETRIEVAL_K}),
                expanded_query="",
                sub_agent_response="",
            ),
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_retrieve, (index, question)): index
            for index, question in enumerate(refined_subquestions)
        }
        for future in as_completed(futures):
            index, item = future.result()
            output[index] = item

    seeded = [item for item in output if item is not None]
    logger.info("Refinement retrieval complete count=%s", len(seeded))
    return seeded


def run_runtime_agent(
    payload: RuntimeAgentRunRequest,
    db: Session,
    model: BaseChatModel | None = None,
    vector_store: Any | None = None,
) -> RuntimeAgentRunResponse:
    """Run the coordinator runtime agent for a user query."""
    run_metadata = build_graph_run_metadata()
    selected_model: BaseChatModel | str = model if model is not None else _RUNTIME_AGENT_MODEL
    logger.info(
        "Runtime agent run start query=%s query_length=%s provided_model=%s provided_vector_store=%s run_id=%s trace_id=%s correlation_id=%s",
        _truncate_query(payload.query),
        len(payload.query),
        model is not None,
        vector_store is not None,
        run_metadata.run_id,
        run_metadata.trace_id,
        run_metadata.correlation_id,
    )
    logger.info(
        "Runtime timeout config loaded vector_store=%ss initial_search=%ss decomposition_llm=%ss coordinator_invoke=%ss document_validation=%ss rerank=%ss subanswer_generation=%ss subanswer_verification=%ss subquestion_pipeline_total=%ss initial_answer=%ss refinement_decision=%ss refinement_decomposition=%ss refinement_retrieval=%ss refinement_pipeline_total=%ss refined_answer=%ss",
        _RUNTIME_TIMEOUT_CONFIG.vector_store_acquisition_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.initial_search_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.decomposition_llm_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.coordinator_invoke_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.document_validation_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.rerank_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.subanswer_generation_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.subanswer_verification_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.subquestion_pipeline_total_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.initial_answer_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.refinement_decision_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.refinement_decomposition_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.refinement_retrieval_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.refinement_pipeline_total_timeout_s,
        _RUNTIME_TIMEOUT_CONFIG.refined_answer_timeout_s,
    )
    selected_vector_store = vector_store
    if selected_vector_store is None:
        try:
            selected_vector_store = _run_with_timeout(
                timeout_s=_RUNTIME_TIMEOUT_CONFIG.vector_store_acquisition_timeout_s,
                operation_name="vector_store_acquisition",
                fn=lambda: get_vector_store(
                    connection=DATABASE_URL,
                    collection_name=_VECTOR_COLLECTION_NAME,
                    embeddings=get_embedding_model(),
                ),
            )
        except FuturesTimeoutError:
            logger.warning(
                "Runtime agent short-circuiting due to vector store timeout query=%s",
                _truncate_query(payload.query),
            )
            return RuntimeAgentRunResponse(
                main_question=payload.query,
                sub_qa=[],
                output=_VECTOR_STORE_TIMEOUT_FALLBACK_MESSAGE,
            )
        logger.info(
            "Runtime agent vector store selected source=default collection_name=%s",
            _VECTOR_COLLECTION_NAME,
        )
    else:
        logger.info("Runtime agent vector store selected source=provided")
    def _build_initial_context_payload() -> tuple[list[Any], list[dict[str, Any]]]:
        docs = search_documents_for_context(
            vector_store=selected_vector_store,
            query=payload.query,
            k=_INITIAL_SEARCH_CONTEXT_K,
            score_threshold=_INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD,
        )
        return docs, build_initial_search_context(docs)

    try:
        initial_context_docs, initial_search_context = _run_with_timeout(
            timeout_s=_RUNTIME_TIMEOUT_CONFIG.initial_search_timeout_s,
            operation_name="initial_search_context_build",
            fn=_build_initial_context_payload,
        )
        logger.info(
            "Initial decomposition context built query=%s docs=%s k=%s score_threshold=%s",
            _truncate_query(payload.query),
            len(initial_search_context),
            _INITIAL_SEARCH_CONTEXT_K,
            _INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD,
        )
    except FuturesTimeoutError:
        initial_context_docs = []
        initial_search_context = []
        logger.warning(
            "Initial decomposition context timeout; continuing with empty context query=%s timeout_s=%s",
            _truncate_query(payload.query),
            _RUNTIME_TIMEOUT_CONFIG.initial_search_timeout_s,
        )
    decomposition_output = run_decomposition_node(
        node_input=DecomposeNodeInput(
            main_question=payload.query,
            run_metadata=run_metadata,
            initial_search_context=initial_search_context,
        ),
        model=model,
        timeout_s=_RUNTIME_TIMEOUT_CONFIG.decomposition_llm_timeout_s,
    )
    decomposition_sub_questions = decomposition_output.decomposition_sub_questions
    agent = create_coordinator_agent(
        vector_store=selected_vector_store,
        model=selected_model,
    )
    search_db_capture = SearchDatabaseCaptureCallback()
    callbacks = [AgentLoggingCallbackHandler(), search_db_capture]
    langfuse_callback = build_langfuse_callback_handler()
    if langfuse_callback is not None:
        callbacks.append(langfuse_callback)
    run_thread_id = run_metadata.thread_id
    logger.info(
        "Runtime agent callback configuration callback_count=%s langfuse_enabled=%s thread_id=%s run_id=%s trace_id=%s correlation_id=%s",
        len(callbacks),
        langfuse_callback is not None,
        run_thread_id,
        run_metadata.run_id,
        run_metadata.trace_id,
        run_metadata.correlation_id,
    )
    config = {"callbacks": callbacks, "configurable": {"thread_id": run_thread_id}}
    coordinator_message = _build_coordinator_input_message(decomposition_sub_questions)
    logger.info(
        "Coordinator sub-question input prepared parsed_sub_questions=%s sub_questions=%s",
        len(decomposition_sub_questions),
        json.dumps(decomposition_sub_questions, ensure_ascii=True),
    )
    coordinator_timed_out = False
    try:
        result = _run_with_timeout(
            timeout_s=_RUNTIME_TIMEOUT_CONFIG.coordinator_invoke_timeout_s,
            operation_name="coordinator_invoke",
            fn=lambda: agent.invoke(
                {"messages": [HumanMessage(content=coordinator_message)]},
                config=config,
            ),
        )
    except FuturesTimeoutError:
        coordinator_timed_out = True
        result = {"messages": []}
        logger.warning(
            "Coordinator invoke timeout; continuing with fallback sub_qa query=%s timeout_s=%s decomposition_sub_question_count=%s",
            _truncate_query(payload.query),
            _RUNTIME_TIMEOUT_CONFIG.coordinator_invoke_timeout_s,
            len(decomposition_sub_questions),
        )
    finally:
        flush_langfuse_callback_handler(langfuse_callback)
    messages = result.get("messages") if isinstance(result, dict) else []
    if isinstance(messages, list) and messages:
        logger.info("Agent run finished; logging tool calls and tool results from %s messages", len(messages))
        log_agent_messages_summary(messages)
    search_database_calls = search_db_capture.get_calls()
    logger.info("Per-subquestion search callbacks captured count=%s", len(search_database_calls))
    sub_qa = _extract_sub_qa(
        messages if isinstance(messages, list) else [],
        search_database_calls=search_database_calls if search_database_calls else None,
    )
    if coordinator_timed_out and not sub_qa:
        sub_qa = _build_fallback_sub_qa_from_decomposition(decomposition_sub_questions)
    elif coordinator_timed_out and sub_qa:
        logger.info(
            "Coordinator timeout fallback not needed; using partial captured sub_qa count=%s",
            len(sub_qa),
        )
    sub_qa = run_pipeline_for_subquestions_with_timeout(
        sub_qa=sub_qa,
        total_timeout_s=_RUNTIME_TIMEOUT_CONFIG.subquestion_pipeline_total_timeout_s,
    )
    _log_sub_qa_run_end_summary(sub_qa)
    coordinator_output = ""
    try:
        coordinator_output = _extract_last_message_content(result)
    except ValueError:
        logger.warning(
            "Coordinator raw output unavailable; continuing with synthesized answer from sub_qa query=%s",
            _truncate_query(payload.query),
        )
    else:
        logger.info(
            "Coordinator raw output captured output_length=%s output_preview=%s",
            len(coordinator_output),
            coordinator_output[:200] + "..." if len(coordinator_output) > 200 else coordinator_output,
        )
    try:
        output = _run_with_timeout(
            timeout_s=_RUNTIME_TIMEOUT_CONFIG.initial_answer_timeout_s,
            operation_name="initial_answer_generation",
            fn=lambda: generate_initial_answer(
                main_question=payload.query,
                initial_search_context=initial_search_context,
                sub_qa=sub_qa,
            ),
        )
        logger.info(
            "Initial answer generation completed within timeout timeout_s=%s output_length=%s",
            _RUNTIME_TIMEOUT_CONFIG.initial_answer_timeout_s,
            len(output),
        )
    except FuturesTimeoutError:
        output = _build_initial_answer_timeout_fallback(sub_qa)
        logger.warning(
            "Initial answer generation timeout; continuing with partial fallback query=%s timeout_s=%s fallback_length=%s",
            _truncate_query(payload.query),
            _RUNTIME_TIMEOUT_CONFIG.initial_answer_timeout_s,
            len(output),
        )
    try:
        refinement_decision = _run_with_timeout(
            timeout_s=_RUNTIME_TIMEOUT_CONFIG.refinement_decision_timeout_s,
            operation_name="refinement_decision",
            fn=lambda: should_refine(
                question=payload.query,
                initial_answer=output,
                sub_qa=sub_qa,
            ),
        )
    except FuturesTimeoutError:
        refinement_decision = type(
            "RefinementDecision",
            (),
            {"refinement_needed": False, "reason": "refinement_decision_timed_out"},
        )()
        logger.warning(
            "Refinement decision timeout; continuing without refinement query=%s timeout_s=%s",
            _truncate_query(payload.query),
            _RUNTIME_TIMEOUT_CONFIG.refinement_decision_timeout_s,
        )
    logger.info(
        "Refinement decision computed refinement_needed=%s reason=%s sub_qa_count=%s",
        refinement_decision.refinement_needed,
        _truncate_query(refinement_decision.reason),
        len(sub_qa),
    )
    if refinement_decision.refinement_needed:
        logger.info(
            "Refinement path flagged refinement_needed=%s reason=%s",
            refinement_decision.refinement_needed,
            _truncate_query(refinement_decision.reason),
        )
        try:
            refined_subquestions = _run_with_timeout(
                timeout_s=_RUNTIME_TIMEOUT_CONFIG.refinement_decomposition_timeout_s,
                operation_name="refinement_decomposition",
                fn=lambda: refine_subquestions(
                    question=payload.query,
                    initial_answer=output,
                    sub_qa=sub_qa,
                ),
            )
        except FuturesTimeoutError:
            refined_subquestions = []
            logger.warning(
                "Refinement decomposition timeout; continuing with initial answer query=%s timeout_s=%s",
                _truncate_query(payload.query),
                _RUNTIME_TIMEOUT_CONFIG.refinement_decomposition_timeout_s,
            )
        logger.info(
            "Refinement decomposition complete reason=%s refined_subquestion_count=%s",
            _truncate_query(refinement_decision.reason),
            len(refined_subquestions),
        )
        for index, refined_subquestion in enumerate(refined_subquestions, start=1):
            logger.info(
                "RefinedSubQuestion[%s]=%s",
                index,
                _truncate_query(refined_subquestion),
            )
        if not refined_subquestions:
            logger.warning(
                "Refinement decomposition produced no refined sub-questions; Section 14 will have no refinement inputs"
            )
        else:
            logger.info(
                "Refined sub-questions prepared for Section 14 handoff count=%s",
                len(refined_subquestions),
            )
            try:
                refined_seed_sub_qa = _run_with_timeout(
                    timeout_s=_RUNTIME_TIMEOUT_CONFIG.refinement_retrieval_timeout_s,
                    operation_name="refinement_retrieval",
                    fn=lambda: _seed_refined_sub_qa_from_retrieval(
                        vector_store=selected_vector_store,
                        refined_subquestions=refined_subquestions,
                    ),
                )
                logger.info(
                    "Refinement retrieval completed within timeout timeout_s=%s seeded_count=%s",
                    _RUNTIME_TIMEOUT_CONFIG.refinement_retrieval_timeout_s,
                    len(refined_seed_sub_qa),
                )
            except FuturesTimeoutError:
                refined_seed_sub_qa = []
                logger.warning(
                    "Refinement retrieval timeout; continuing with initial answer query=%s timeout_s=%s",
                    _truncate_query(payload.query),
                    _RUNTIME_TIMEOUT_CONFIG.refinement_retrieval_timeout_s,
                )
            if not refined_seed_sub_qa:
                logger.warning(
                    "Refinement retrieval produced no seeded sub-questions; keeping initial answer output"
                )
                logger.info(
                    "Refinement answer path skipped due to empty seeded retrieval results refined_subquestion_count=%s",
                    len(refined_subquestions),
                )
                logger.info(
                    "Runtime agent run complete output_length=%s output_preview=%s",
                    len(output),
                    output[:200] + "..." if len(output) > 200 else output,
                )
                return RuntimeAgentRunResponse(
                    main_question=payload.query,
                    sub_qa=sub_qa,
                    output=output,
                )
            logger.info(
                "Refinement per-subquestion pipeline start count=%s total_timeout_s=%s",
                len(refined_seed_sub_qa),
                _RUNTIME_TIMEOUT_CONFIG.refinement_pipeline_total_timeout_s,
            )
            refined_sub_qa = run_pipeline_for_subquestions_with_timeout(
                sub_qa=refined_seed_sub_qa,
                total_timeout_s=_RUNTIME_TIMEOUT_CONFIG.refinement_pipeline_total_timeout_s,
            )
            _log_sub_qa_run_end_summary(refined_sub_qa)
            try:
                refined_output = _run_with_timeout(
                    timeout_s=_RUNTIME_TIMEOUT_CONFIG.refined_answer_timeout_s,
                    operation_name="refined_answer_generation",
                    fn=lambda: generate_initial_answer(
                        main_question=payload.query,
                        initial_search_context=initial_search_context,
                        sub_qa=refined_sub_qa,
                    ),
                )
                logger.info(
                    "Refinement answer generation completed within timeout timeout_s=%s refined_sub_qa_count=%s refined_output_length=%s",
                    _RUNTIME_TIMEOUT_CONFIG.refined_answer_timeout_s,
                    len(refined_sub_qa),
                    len(refined_output),
                )
                output = refined_output
            except FuturesTimeoutError:
                logger.warning(
                    "Refined answer generation timeout; keeping initial answer query=%s timeout_s=%s initial_output_length=%s",
                    _truncate_query(payload.query),
                    _RUNTIME_TIMEOUT_CONFIG.refined_answer_timeout_s,
                    len(output),
                )
            sub_qa = refined_sub_qa
    logger.info(
        "Runtime agent run complete output_length=%s output_preview=%s",
        len(output),
        output[:200] + "..." if len(output) > 200 else output,
    )
    return RuntimeAgentRunResponse(
        main_question=payload.query,
        sub_qa=sub_qa,
        output=output,
    )
