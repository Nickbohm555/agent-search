from __future__ import annotations

import ast
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from agents import create_coordinator_agent, get_decomposition_only_prompt
from db import DATABASE_URL
from schemas import RuntimeAgentRunRequest, RuntimeAgentRunResponse, SubQuestionAnswer
from services.document_validation_service import (
    RetrievedDocument,
    build_document_validation_config_from_env,
    format_retrieved_documents,
    parse_retrieved_documents,
    validate_subquestion_documents,
)
from services.reranker_service import build_reranker_config_from_env, rerank_documents
from services.initial_answer_service import generate_initial_answer
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
    search_documents_for_context,
)
from utils.agent_callbacks import (
    AgentLoggingCallbackHandler,
    SearchDatabaseCaptureCallback,
    log_agent_messages_summary,
)
from utils.embeddings import get_embedding_model
from utils.langfuse_tracing import (
    build_langfuse_callback_handler,
    flush_langfuse_callback_handler,
)

logger = logging.getLogger(__name__)

_VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")
_RUNTIME_AGENT_MODEL = os.getenv("RUNTIME_AGENT_MODEL", "gpt-4.1-mini")
_DECOMPOSITION_ONLY_MODEL = os.getenv("DECOMPOSITION_ONLY_MODEL", _RUNTIME_AGENT_MODEL)
_DECOMPOSITION_ONLY_TEMPERATURE = float(os.getenv("DECOMPOSITION_ONLY_TEMPERATURE", "0"))
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
_MAIN_AGENT_TASK_TOOL_NAME = "task"
_SEARCH_DATABASE_TOOL_NAME = "search_database"


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
_SUBQUESTION_PIPELINE_MAX_WORKERS = int(os.getenv("SUBQUESTION_PIPELINE_MAX_WORKERS", "4"))
_REFINEMENT_RETRIEVAL_K = max(1, int(os.getenv("REFINEMENT_RETRIEVAL_K", "10")))


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


def _parse_decomposition_output(*, raw_output: str, query: str) -> list[str]:
    fallback_question = _normalize_sub_question(query) or "What is the main question?"
    text = (raw_output or "").strip()
    if not text:
        logger.warning("Decomposition output empty; using fallback question")
        return [fallback_question]

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
        return normalized

    logger.warning(
        "Decomposition output malformed; using fallback question output_preview=%s",
        _truncate_query(text),
    )
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
) -> str:
    fallback_question = _normalize_sub_question(query) or f"{query.strip()}?"
    if model is None and not _OPENAI_API_KEY:
        logger.info(
            "Decomposition-only LLM call using fallback; OPENAI_API_KEY is not set model=%s",
            _DECOMPOSITION_ONLY_MODEL,
        )
        return json.dumps([fallback_question], ensure_ascii=True)

    messages = [
        SystemMessage(content=get_decomposition_only_prompt()),
        HumanMessage(content=_build_decomposition_only_input_message(query, initial_search_context)),
    ]
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
        response = llm.invoke(messages)
        content = _stringify_message_content(getattr(response, "content", "")).strip()
        if content:
            return content
        logger.warning(
            "Decomposition-only LLM call returned empty content; using fallback model=%s",
            _DECOMPOSITION_ONLY_MODEL,
        )
    except Exception:
        logger.exception(
            "Decomposition-only LLM call failed; using fallback model=%s",
            _DECOMPOSITION_ONLY_MODEL,
        )
    return json.dumps([fallback_question], ensure_ascii=True)


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
        "Per-subquestion reranking start count=%s top_n=%s title_weight=%s content_weight=%s source_weight=%s original_rank_bias=%s",
        len(sub_qa),
        _RERANKER_CONFIG.top_n,
        _RERANKER_CONFIG.title_weight,
        _RERANKER_CONFIG.content_weight,
        _RERANKER_CONFIG.source_weight,
        _RERANKER_CONFIG.original_rank_bias,
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
    working_item = _apply_document_validation_to_sub_qa([working_item])[0]
    working_item = _apply_reranking_to_sub_qa([working_item])[0]
    reranked_output = working_item.sub_answer
    working_item = _apply_subanswer_generation_to_sub_qa([working_item])[0]
    working_item = _apply_subanswer_verification_to_sub_qa(
        [working_item],
        reranked_output_by_sub_question={working_item.sub_question: reranked_output},
    )[0]
    logger.info(
        "Per-subquestion pipeline item complete sub_question=%s answerable=%s reason=%s",
        _truncate_query(working_item.sub_question),
        working_item.answerable,
        _truncate_query(working_item.verification_reason),
    )
    return working_item


def run_pipeline_for_subquestions(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]:
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
        for future in as_completed(futures):
            index = futures[future]
            output[index] = future.result()
    processed = [item for item in output if item is not None]
    logger.info(
        "Per-subquestion pipeline parallel complete count=%s",
        len(processed),
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
    selected_model: BaseChatModel | str = model if model is not None else _RUNTIME_AGENT_MODEL
    logger.info(
        "Runtime agent run start query=%s query_length=%s provided_model=%s provided_vector_store=%s",
        _truncate_query(payload.query),
        len(payload.query),
        model is not None,
        vector_store is not None,
    )
    selected_vector_store = vector_store
    if selected_vector_store is None:
        selected_vector_store = get_vector_store(
            connection=DATABASE_URL,
            collection_name=_VECTOR_COLLECTION_NAME,
            embeddings=get_embedding_model(),
        )
        logger.info(
            "Runtime agent vector store selected source=default collection_name=%s",
            _VECTOR_COLLECTION_NAME,
        )
    else:
        logger.info("Runtime agent vector store selected source=provided")
    initial_context_docs = search_documents_for_context(
        vector_store=selected_vector_store,
        query=payload.query,
        k=_INITIAL_SEARCH_CONTEXT_K,
        score_threshold=_INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD,
    )
    initial_search_context = build_initial_search_context(initial_context_docs)
    logger.info(
        "Initial decomposition context built query=%s docs=%s k=%s score_threshold=%s",
        _truncate_query(payload.query),
        len(initial_search_context),
        _INITIAL_SEARCH_CONTEXT_K,
        _INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD,
    )
    decomposition_raw_output = _run_decomposition_only_llm_call(
        query=payload.query,
        initial_search_context=initial_search_context,
        model=model,
    )
    logger.info(
        "Decomposition-only LLM output captured output_length=%s output_preview=%s",
        len(decomposition_raw_output),
        _truncate_query(decomposition_raw_output),
    )
    decomposition_sub_questions = _parse_decomposition_output(
        raw_output=decomposition_raw_output,
        query=payload.query,
    )
    logger.info(
        "Decomposition output parsed sub_question_count=%s sub_questions=%s",
        len(decomposition_sub_questions),
        json.dumps(decomposition_sub_questions, ensure_ascii=True),
    )
    agent = create_coordinator_agent(
        vector_store=selected_vector_store,
        model=selected_model,
    )
    search_db_capture = SearchDatabaseCaptureCallback()
    callbacks = [AgentLoggingCallbackHandler(), search_db_capture]
    langfuse_callback = build_langfuse_callback_handler()
    if langfuse_callback is not None:
        callbacks.append(langfuse_callback)
    logger.info(
        "Runtime agent callback configuration callback_count=%s langfuse_enabled=%s",
        len(callbacks),
        langfuse_callback is not None,
    )
    config = {"callbacks": callbacks}
    coordinator_message = _build_coordinator_input_message(decomposition_sub_questions)
    logger.info(
        "Coordinator sub-question input prepared parsed_sub_questions=%s sub_questions=%s",
        len(decomposition_sub_questions),
        json.dumps(decomposition_sub_questions, ensure_ascii=True),
    )
    try:
        result = agent.invoke(
            {"messages": [HumanMessage(content=coordinator_message)]},
            config=config,
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
    sub_qa = run_pipeline_for_subquestions(sub_qa)
    _log_sub_qa_run_end_summary(sub_qa)
    coordinator_output = _extract_last_message_content(result)
    logger.info(
        "Coordinator raw output captured output_length=%s output_preview=%s",
        len(coordinator_output),
        coordinator_output[:200] + "..." if len(coordinator_output) > 200 else coordinator_output,
    )
    output = generate_initial_answer(
        main_question=payload.query,
        initial_search_context=initial_search_context,
        sub_qa=sub_qa,
    )
    refinement_decision = should_refine(
        question=payload.query,
        initial_answer=output,
        sub_qa=sub_qa,
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
        refined_subquestions = refine_subquestions(
            question=payload.query,
            initial_answer=output,
            sub_qa=sub_qa,
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
            refined_seed_sub_qa = _seed_refined_sub_qa_from_retrieval(
                vector_store=selected_vector_store,
                refined_subquestions=refined_subquestions,
            )
            refined_sub_qa = run_pipeline_for_subquestions(refined_seed_sub_qa)
            _log_sub_qa_run_end_summary(refined_sub_qa)
            refined_output = generate_initial_answer(
                main_question=payload.query,
                initial_search_context=initial_search_context,
                sub_qa=refined_sub_qa,
            )
            logger.info(
                "Refinement answer path complete refined_sub_qa_count=%s refined_output_length=%s",
                len(refined_sub_qa),
                len(refined_output),
            )
            output = refined_output
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
