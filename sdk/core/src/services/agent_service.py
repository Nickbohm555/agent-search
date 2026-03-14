from __future__ import annotations

import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from agent_search.runtime.reducers import (
    merge_citation_rows_by_index,
    merge_decomposition_sub_questions,
    merge_stage_snapshots,
    merge_sub_qa,
    merge_sub_question_artifacts,
)
from agent_search.config import RuntimeConfig as RequestRuntimeConfig
from agent_search.runtime.state import RAGState, from_rag_state, to_rag_state
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
    GraphStageSnapshot,
    RerankNodeInput,
    RerankNodeOutput,
    SearchNodeInput,
    SearchNodeOutput,
    SynthesizeFinalNodeInput,
    SynthesizeFinalNodeOutput,
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
from services.reranker_service import RerankerConfig, build_reranker_config_from_env, rerank_documents
from services.initial_answer_service import generate_final_synthesis_answer, generate_initial_answer
from services.query_expansion_service import (
    QueryExpansionConfig,
    build_query_expansion_config_from_env,
    expand_queries_for_subquestion,
)
from services.refinement_decomposition_service import refine_subquestions
from services.refinement_decision_service import should_refine
from services.subanswer_service import generate_subanswer
from services.subanswer_verification_service import SubanswerVerificationResult, verify_subanswer
from services.vector_store_service import (
    search_documents_for_queries,
    search_documents_for_context,
)
from utils.agent_callbacks import AgentLoggingCallbackHandler
from utils.langfuse_tracing import (
    build_langfuse_run_metadata,
    flush_langfuse_callback_handler,
)

logger = logging.getLogger(__name__)

_VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")
_RUNTIME_AGENT_MODEL = os.getenv("RUNTIME_AGENT_MODEL", "gpt-4.1-mini")
_DECOMPOSITION_ONLY_MODEL = os.getenv("DECOMPOSITION_ONLY_MODEL", _RUNTIME_AGENT_MODEL)
_DECOMPOSITION_ONLY_TEMPERATURE = float(os.getenv("DECOMPOSITION_ONLY_TEMPERATURE", "0"))
_DECOMPOSITION_ONLY_MAX_SUBQUESTIONS_RAW = os.getenv("DECOMPOSITION_ONLY_MAX_SUBQUESTIONS", "8")
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
_VECTOR_STORE_TIMEOUT_FALLBACK_MESSAGE = (
    "Knowledge base retrieval is temporarily unavailable. Please try again in a moment."
)
_INITIAL_ANSWER_FALLBACK_PREFIX = "Partial context only."
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
_GRAPH_RUNNER_MAX_WORKERS = max(1, int(os.getenv("GRAPH_RUNNER_MAX_WORKERS", "4")))
_REFINEMENT_RETRIEVAL_K = max(1, int(os.getenv("REFINEMENT_RETRIEVAL_K", "10")))
_SEARCH_NODE_K_FETCH = max(1, int(os.getenv("SEARCH_NODE_K_FETCH", "10")))
_SEARCH_NODE_SCORE_THRESHOLD_RAW = os.getenv("SEARCH_NODE_SCORE_THRESHOLD", "0.0")
try:
    _SEARCH_NODE_SCORE_THRESHOLD = (
        float(_SEARCH_NODE_SCORE_THRESHOLD_RAW) if _SEARCH_NODE_SCORE_THRESHOLD_RAW not in (None, "") else None
    )
except ValueError:
    _SEARCH_NODE_SCORE_THRESHOLD = None
_SEARCH_NODE_MERGED_CAP = max(1, int(os.getenv("SEARCH_NODE_MERGED_CAP", "30")))
_ANSWER_SUBQUESTION_NO_SUPPORT_FALLBACK = "nothing relevant found"
_CITATION_INDEX_PATTERN = re.compile(r"\[(\d+)\]")
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


@dataclass(frozen=True)
class RuntimeTimeoutConfig:
    vector_store_acquisition_timeout_s: int
    initial_search_timeout_s: int
    decomposition_llm_timeout_s: int
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
        document_validation_timeout_s=_read_timeout_seconds("DOCUMENT_VALIDATION_TIMEOUT_S", 20),
        rerank_timeout_s=_read_timeout_seconds("RERANK_TIMEOUT_S", 1),
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


def _run_pipeline_for_single_subquestion(item: SubQuestionAnswer) -> SubQuestionAnswer:
    working_item = item.model_copy(deep=True)
    logger.info(
        "Per-subquestion pipeline item start sub_question=%s",
        _truncate_query(working_item.sub_question),
    )
    working_item = _apply_document_validation_to_sub_qa([working_item])[0]
    working_item = _apply_reranking_to_sub_qa([working_item])[0]
    working_item = _apply_subanswer_generation_to_sub_qa([working_item])[0]
    working_item.answerable = True
    working_item.verification_reason = "citation_supported"
    logger.info(
        "Per-subquestion pipeline item complete sub_question=%s answerable=%s reason=%s",
        _truncate_query(working_item.sub_question),
        working_item.answerable,
        _truncate_query(working_item.verification_reason),
    )
    return working_item


def run_pipeline_for_subquestions(sub_qa: list[SubQuestionAnswer]) -> list[SubQuestionAnswer]:
    return run_pipeline_for_subquestions_with_timeout(sub_qa=sub_qa, total_timeout_s=None)


def _build_initial_answer_timeout_fallback(sub_qa: list[SubQuestionAnswer]) -> str:
    partial_answers = [item.sub_answer.strip() for item in sub_qa if isinstance(item.sub_answer, str) and item.sub_answer.strip()]
    if not partial_answers:
        return _INITIAL_ANSWER_FALLBACK_PREFIX
    joined = " ".join(partial_answers)
    return f"{_INITIAL_ANSWER_FALLBACK_PREFIX} {joined}"


def _build_callbacks(
    *,
    external_callbacks: list[Any] | None = None,
    external_langfuse_callback: Any | None = None,
    sampling_key: str | None = None,
) -> tuple[list[Any], Any | None]:
    _ = sampling_key
    callbacks: list[Any] = [AgentLoggingCallbackHandler()]
    if external_callbacks:
        callbacks.extend(external_callbacks)
    langfuse_callback = external_langfuse_callback
    if langfuse_callback is not None and langfuse_callback not in callbacks:
        callbacks.append(langfuse_callback)
    return callbacks, langfuse_callback


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


def _find_sub_question_artifact(
    *,
    state: RAGState,
    sub_question: str,
) -> SubQuestionArtifacts | None:
    return next((item for item in state["sub_question_artifacts"] if item.sub_question == sub_question), None)


def _find_sub_qa_item(
    *,
    state: RAGState,
    sub_question: str,
) -> SubQuestionAnswer | None:
    return next((item for item in state["sub_qa"] if item.sub_question == sub_question), None)


def build_agent_graph_state(
    *,
    main_question: str,
    decomposition_sub_questions: list[str] | None = None,
    sub_qa: list[SubQuestionAnswer] | None = None,
    final_answer: str = "",
    run_metadata: GraphRunMetadata | None = None,
) -> AgentGraphState:
    normalized_sub_qa = [item.model_copy(deep=True) for item in (sub_qa or [])]
    artifacts: list[SubQuestionArtifacts] = []
    citation_rows_by_index: dict[int, CitationSourceRow] = {}
    for index, item in enumerate(normalized_sub_qa, start=1):
        artifact = _build_subquestion_artifact_from_subqa(item, rank=index)
        artifacts = merge_sub_question_artifacts(artifacts, [artifact])
        citation_rows_by_index = merge_citation_rows_by_index(citation_rows_by_index, artifact.citation_rows_by_index)

    resolved_decomposition = decomposition_sub_questions or [item.sub_question for item in normalized_sub_qa]
    resolved_metadata = run_metadata or build_graph_run_metadata()
    resolved_output = final_answer.strip()
    rag_state = RAGState(
        main_question=main_question,
        decomposition_sub_questions=merge_decomposition_sub_questions([], resolved_decomposition),
        sub_question_artifacts=artifacts,
        final_answer=resolved_output,
        citation_rows_by_index=citation_rows_by_index,
        run_metadata=resolved_metadata,
        sub_qa=merge_sub_qa([], normalized_sub_qa),
        output=resolved_output,
        stage_snapshots=merge_stage_snapshots([], []),
    )
    state = from_rag_state(rag_state)
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


def map_graph_state_to_runtime_response(state: AgentGraphState | RAGState) -> RuntimeAgentRunResponse:
    rag_state = to_rag_state(state)
    output = rag_state["output"].strip() or rag_state["final_answer"]
    citation_indices = _extract_citation_indices(output)
    final_citations = [
        rag_state["citation_rows_by_index"][index].model_copy(deep=True)
        for index in sorted(set(citation_indices))
        if index in rag_state["citation_rows_by_index"]
    ]
    response = RuntimeAgentRunResponse(
        main_question=rag_state["main_question"],
        sub_items=[(item.sub_question, item.sub_answer) for item in rag_state["sub_qa"]],
        output=output,
        final_citations=final_citations,
    )
    logger.info(
        "Agent graph state mapped to runtime response sub_qa_count=%s output_len=%s run_id=%s",
        len(response.sub_items),
        len(response.output),
        rag_state["run_metadata"].run_id,
    )
    return response


def apply_decompose_node_output_to_graph_state(
    *,
    state: AgentGraphState | RAGState,
    node_output: DecomposeNodeOutput,
) -> AgentGraphState:
    next_state = to_rag_state(state)
    decomposition_sub_questions = merge_decomposition_sub_questions([], node_output.decomposition_sub_questions)
    next_state["decomposition_sub_questions"] = decomposition_sub_questions
    next_state["sub_question_artifacts"] = merge_sub_question_artifacts(
        [],
        [SubQuestionArtifacts(sub_question=item) for item in decomposition_sub_questions],
    )
    next_state["sub_qa"] = merge_sub_qa(
        [],
        [
            SubQuestionAnswer(
                sub_question=item,
                sub_answer="",
                tool_call_input=json.dumps({"query": item}, ensure_ascii=True),
                expanded_query="",
                sub_agent_response="",
                answerable=False,
                verification_reason="",
            )
            for item in decomposition_sub_questions
        ],
    )
    logger.info(
        "Decomposition node state update sub_question_count=%s run_id=%s",
        len(decomposition_sub_questions),
        next_state["run_metadata"].run_id,
    )
    return from_rag_state(next_state)


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
    state: AgentGraphState | RAGState,
    sub_question: str,
    node_output: ExpandNodeOutput,
) -> AgentGraphState:
    next_state = to_rag_state(state)
    current_artifact = _find_sub_question_artifact(state=next_state, sub_question=sub_question)
    artifact = (
        current_artifact.model_copy(deep=True)
        if current_artifact is not None
        else SubQuestionArtifacts(sub_question=sub_question)
    )
    artifact.expanded_queries = list(node_output.expanded_queries)
    next_state["sub_question_artifacts"] = merge_sub_question_artifacts(
        next_state["sub_question_artifacts"],
        [artifact],
    )

    compat_expanded_query = _select_compat_expanded_query(
        sub_question=sub_question,
        expanded_queries=node_output.expanded_queries,
    )
    current_sub_qa = _find_sub_qa_item(state=next_state, sub_question=sub_question)
    if current_sub_qa is not None:
        updated_sub_qa = current_sub_qa.model_copy(deep=True)
        updated_sub_qa.expanded_query = compat_expanded_query
        next_state["sub_qa"] = merge_sub_qa(next_state["sub_qa"], [updated_sub_qa])

    logger.info(
        "Expansion node state update sub_question=%s expanded_query_count=%s compat_expanded_query=%s run_id=%s",
        _truncate_query(sub_question),
        len(node_output.expanded_queries),
        _truncate_query(compat_expanded_query),
        next_state["run_metadata"].run_id,
    )
    return from_rag_state(next_state)


def run_search_node(
    *,
    node_input: SearchNodeInput,
    vector_store: Any,
    k_fetch: int | None = None,
) -> SearchNodeOutput:
    from agent_search.runtime.nodes.search import run_search_node as run_runtime_search_node

    return run_runtime_search_node(
        node_input=node_input,
        vector_store=vector_store,
        k_fetch=k_fetch,
        score_threshold=_SEARCH_NODE_SCORE_THRESHOLD,
        merged_cap=_SEARCH_NODE_MERGED_CAP,
        search_documents_for_queries_fn=search_documents_for_queries,
        assert_vector_store_compatible_fn=lambda store: store,
        truncate_query_fn=_truncate_query,
    )


def apply_search_node_output_to_graph_state(
    *,
    state: AgentGraphState | RAGState,
    sub_question: str,
    node_output: SearchNodeOutput,
) -> AgentGraphState:
    next_state = to_rag_state(state)
    current_artifact = _find_sub_question_artifact(state=next_state, sub_question=sub_question)
    artifact = (
        current_artifact.model_copy(deep=True)
        if current_artifact is not None
        else SubQuestionArtifacts(sub_question=sub_question)
    )
    artifact.retrieved_docs = [row.model_copy(deep=True) for row in node_output.retrieved_docs]
    artifact.retrieval_provenance = list(node_output.retrieval_provenance)
    artifact.citation_rows_by_index = {
        key: value.model_copy(deep=True)
        for key, value in node_output.citation_rows_by_index.items()
    }
    next_state["sub_question_artifacts"] = merge_sub_question_artifacts(
        next_state["sub_question_artifacts"],
        [artifact],
    )

    next_state["citation_rows_by_index"] = merge_citation_rows_by_index(
        next_state["citation_rows_by_index"],
        node_output.citation_rows_by_index,
    )

    retrieved_output = _format_citation_rows_for_pipeline(node_output.retrieved_docs)
    compat_input_payload = {
        "query": sub_question,
        "expanded_queries": list(artifact.expanded_queries),
        "retrieval_provenance": list(node_output.retrieval_provenance),
        "limit": len(node_output.retrieved_docs),
    }
    current_sub_qa = _find_sub_qa_item(state=next_state, sub_question=sub_question)
    matched_sub_qa = (
        current_sub_qa.model_copy(deep=True)
        if current_sub_qa is not None
        else SubQuestionAnswer(sub_question=sub_question, sub_answer="")
    )

    matched_sub_qa.sub_answer = retrieved_output
    matched_sub_qa.tool_call_input = json.dumps(compat_input_payload, ensure_ascii=True)
    matched_sub_qa.expanded_query = _select_compat_expanded_query(
        sub_question=sub_question,
        expanded_queries=artifact.expanded_queries,
    )
    next_state["sub_qa"] = merge_sub_qa(next_state["sub_qa"], [matched_sub_qa])

    logger.info(
        "Search node state update sub_question=%s merged_candidates=%s provenance_events=%s run_id=%s",
        _truncate_query(sub_question),
        len(node_output.retrieved_docs),
        len(node_output.retrieval_provenance),
        next_state["run_metadata"].run_id,
    )
    return from_rag_state(next_state)


def run_rerank_node(
    *,
    node_input: RerankNodeInput,
    config: Any | None = None,
    callbacks: list[Any] | None = None,
) -> RerankNodeOutput:
    from agent_search.runtime.nodes.rerank import run_rerank_node as run_runtime_rerank_node

    return run_runtime_rerank_node(
        node_input=node_input,
        config=config,
        callbacks=callbacks,
        default_config=_RERANKER_CONFIG,
        rerank_documents_fn=rerank_documents,
        truncate_query_fn=_truncate_query,
    )


def apply_rerank_node_output_to_graph_state(
    *,
    state: AgentGraphState | RAGState,
    sub_question: str,
    node_output: RerankNodeOutput,
) -> AgentGraphState:
    next_state = to_rag_state(state)
    current_artifact = _find_sub_question_artifact(state=next_state, sub_question=sub_question)
    artifact = (
        current_artifact.model_copy(deep=True)
        if current_artifact is not None
        else SubQuestionArtifacts(sub_question=sub_question)
    )
    artifact.reranked_docs = [row.model_copy(deep=True) for row in node_output.reranked_docs]
    artifact.citation_rows_by_index = {
        key: value.model_copy(deep=True)
        for key, value in node_output.citation_rows_by_index.items()
    }
    next_state["sub_question_artifacts"] = merge_sub_question_artifacts(
        next_state["sub_question_artifacts"],
        [artifact],
    )
    next_state["citation_rows_by_index"] = merge_citation_rows_by_index(
        next_state["citation_rows_by_index"],
        node_output.citation_rows_by_index,
    )

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
    current_sub_qa = _find_sub_qa_item(state=next_state, sub_question=sub_question)
    matched_sub_qa = (
        current_sub_qa.model_copy(deep=True)
        if current_sub_qa is not None
        else SubQuestionAnswer(sub_question=sub_question, sub_answer="")
    )
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
    next_state["sub_qa"] = merge_sub_qa(next_state["sub_qa"], [matched_sub_qa])

    logger.info(
        "Rerank node state update sub_question=%s reranked_candidates=%s run_id=%s",
        _truncate_query(sub_question),
        len(node_output.reranked_docs),
        next_state["run_metadata"].run_id,
    )
    return from_rag_state(next_state)


def run_answer_subquestion_node(
    *,
    node_input: AnswerSubquestionNodeInput,
    prompt_template: str | None = None,
    callbacks: list[Any] | None = None,
) -> AnswerSubquestionNodeOutput:
    from agent_search.runtime.nodes.answer import run_answer_node as run_runtime_answer_node

    return run_runtime_answer_node(
        node_input=node_input,
        prompt_template=prompt_template,
        callbacks=callbacks,
        no_support_fallback=_ANSWER_SUBQUESTION_NO_SUPPORT_FALLBACK,
        format_citation_rows_for_pipeline_fn=_format_citation_rows_for_pipeline,
        generate_subanswer_fn=generate_subanswer,
        extract_citation_indices_fn=_extract_citation_indices,
        truncate_query_fn=_truncate_query,
    )


def apply_answer_subquestion_node_output_to_graph_state(
    *,
    state: AgentGraphState | RAGState,
    sub_question: str,
    node_output: AnswerSubquestionNodeOutput,
) -> AgentGraphState:
    next_state = to_rag_state(state)
    current_artifact = _find_sub_question_artifact(state=next_state, sub_question=sub_question)
    artifact = (
        current_artifact.model_copy(deep=True)
        if current_artifact is not None
        else SubQuestionArtifacts(sub_question=sub_question)
    )
    artifact.sub_answer = node_output.sub_answer
    artifact.citation_rows_by_index = {
        key: value.model_copy(deep=True)
        for key, value in node_output.citation_rows_by_index.items()
    }
    next_state["sub_question_artifacts"] = merge_sub_question_artifacts(
        next_state["sub_question_artifacts"],
        [artifact],
    )
    next_state["citation_rows_by_index"] = merge_citation_rows_by_index(
        next_state["citation_rows_by_index"],
        node_output.citation_rows_by_index,
    )

    current_sub_qa = _find_sub_qa_item(state=next_state, sub_question=sub_question)
    matched_sub_qa = (
        current_sub_qa.model_copy(deep=True)
        if current_sub_qa is not None
        else SubQuestionAnswer(sub_question=sub_question, sub_answer="")
    )

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
    next_state["sub_qa"] = merge_sub_qa(next_state["sub_qa"], [matched_sub_qa])

    logger.info(
        "Subanswer node state update sub_question=%s answerable=%s citation_count=%s run_id=%s",
        _truncate_query(sub_question),
        node_output.answerable,
        len(node_output.citation_indices_used),
        next_state["run_metadata"].run_id,
    )
    return from_rag_state(next_state)


def run_synthesize_final_node(
    *,
    node_input: SynthesizeFinalNodeInput,
    prompt_template: str | None = None,
    callbacks: list[Any] | None = None,
) -> SynthesizeFinalNodeOutput:
    from agent_search.runtime.nodes.synthesize import run_synthesize_node as run_runtime_synthesize_node

    return run_runtime_synthesize_node(
        node_input=node_input,
        prompt_template=prompt_template,
        callbacks=callbacks,
        generate_final_synthesis_answer_fn=generate_final_synthesis_answer,
        extract_citation_indices_fn=_extract_citation_indices,
        build_initial_answer_timeout_fallback_fn=_build_initial_answer_timeout_fallback,
        truncate_query_fn=_truncate_query,
    )


def apply_synthesize_final_node_output_to_graph_state(
    *,
    state: AgentGraphState | RAGState,
    node_output: SynthesizeFinalNodeOutput,
) -> AgentGraphState:
    next_state = to_rag_state(state)
    resolved_final_answer = (node_output.final_answer or "").strip()
    next_state["final_answer"] = resolved_final_answer
    next_state["output"] = resolved_final_answer
    logger.info(
        "Final synthesis node state update output_len=%s sub_qa_count=%s run_id=%s",
        len(resolved_final_answer),
        len(next_state["sub_qa"]),
        next_state["run_metadata"].run_id,
    )
    return from_rag_state(next_state)


@dataclass(frozen=True)
class _GraphLaneExecutionResult:
    lane_index: int
    lane_total: int
    sub_question: str
    expand_output: ExpandNodeOutput
    search_output: SearchNodeOutput
    rerank_output: RerankNodeOutput
    answer_output: AnswerSubquestionNodeOutput


@dataclass(frozen=True)
class _ResolvedRuntimeExecutionConfig:
    query_expansion_enabled: bool
    query_expansion_config: QueryExpansionConfig
    rerank_config: RerankerConfig
    subanswer_prompt: str | None
    synthesis_prompt: str | None


def _resolve_request_runtime_config(payload: RuntimeAgentRunRequest) -> RequestRuntimeConfig:
    runtime_config_payload: dict[str, Any] = {}
    if payload.runtime_config is not None:
        resolved_runtime_config_payload = payload.runtime_config.model_dump(exclude_none=True)
        if isinstance(resolved_runtime_config_payload, dict):
            runtime_config_payload.update(resolved_runtime_config_payload)
    if payload.custom_prompts is not None:
        custom_prompts_payload = payload.custom_prompts.model_dump(exclude_none=True)
        if custom_prompts_payload:
            runtime_config_payload["custom_prompts"] = custom_prompts_payload
    return RequestRuntimeConfig.from_dict(runtime_config_payload)


def _resolve_runtime_execution_config(payload: RuntimeAgentRunRequest) -> _ResolvedRuntimeExecutionConfig:
    runtime_config = _resolve_request_runtime_config(payload)
    return _ResolvedRuntimeExecutionConfig(
        query_expansion_enabled=runtime_config.query_expansion.enabled,
        query_expansion_config=QueryExpansionConfig(
            model=_QUERY_EXPANSION_CONFIG.model,
            temperature=_QUERY_EXPANSION_CONFIG.temperature,
            max_queries=_QUERY_EXPANSION_CONFIG.max_queries,
            max_query_length=_QUERY_EXPANSION_CONFIG.max_query_length,
        ),
        rerank_config=RerankerConfig(
            enabled=runtime_config.rerank.enabled,
            top_n=_RERANKER_CONFIG.top_n,
            provider=_RERANKER_CONFIG.provider,
            model_name=_RERANKER_CONFIG.model_name,
            openai_model_name=_RERANKER_CONFIG.openai_model_name,
            openai_temperature=_RERANKER_CONFIG.openai_temperature,
        ),
        subanswer_prompt=runtime_config.custom_prompts.subanswer,
        synthesis_prompt=runtime_config.custom_prompts.synthesis,
    )


def _build_query_expansion_bypass_output(*, sub_question: str) -> ExpandNodeOutput:
    logger.info("Expansion node bypassed by runtime config sub_question=%s", _truncate_query(sub_question))
    return ExpandNodeOutput(expanded_queries=[sub_question])


def _build_rerank_bypass_output(*, node_input: RerankNodeInput) -> RerankNodeOutput:
    reranked_docs = [
        CitationSourceRow(
            citation_index=index,
            rank=index,
            title=row.title,
            source=row.source,
            content=row.content,
            document_id=row.document_id,
            score=None,
        )
        for index, row in enumerate(node_input.retrieved_docs, start=1)
    ]
    logger.info(
        "Rerank node bypassed by runtime config sub_question=%s candidate_count=%s run_id=%s",
        _truncate_query(node_input.sub_question),
        len(reranked_docs),
        node_input.run_metadata.run_id,
    )
    return RerankNodeOutput(
        reranked_docs=reranked_docs,
        citation_rows_by_index={row.citation_index: row for row in reranked_docs},
    )


def _emit_graph_state_snapshot(
    *,
    state: AgentGraphState,
    stage: str,
    status: str = "completed",
    sub_question: str = "",
    lane_index: int = 0,
    lane_total: int = 0,
    snapshot_callback: Any | None = None,
) -> None:
    snapshot = GraphStageSnapshot(
        stage=stage,
        status=status,
        sub_question=sub_question,
        lane_index=lane_index,
        lane_total=lane_total,
        decomposition_sub_questions=list(state.decomposition_sub_questions),
        sub_qa=[item.model_copy(deep=True) for item in state.sub_qa],
        sub_question_artifacts=[item.model_copy(deep=True) for item in state.sub_question_artifacts],
        output=state.output,
    )
    state.stage_snapshots = merge_stage_snapshots(state.stage_snapshots, [snapshot])
    if snapshot_callback is not None:
        try:
            snapshot_callback(snapshot, state)
        except Exception:  # noqa: BLE001
            logger.exception(
                "Graph state snapshot callback failed stage=%s run_id=%s",
                stage,
                state.run_metadata.run_id,
            )
    logger.info(
        "Graph state snapshot emitted stage=%s status=%s lane_index=%s lane_total=%s sub_question=%s snapshot_count=%s run_id=%s",
        stage,
        status,
        lane_index,
        lane_total,
        _truncate_query(sub_question),
        len(state.stage_snapshots),
        state.run_metadata.run_id,
    )


def _run_graph_subquestion_lane(
    *,
    main_question: str,
    sub_question: str,
    lane_index: int,
    lane_total: int,
    vector_store: Any,
    model: BaseChatModel | None,
    run_metadata: GraphRunMetadata,
    runtime_execution_config: _ResolvedRuntimeExecutionConfig,
    callbacks: list[Any] | None = None,
    langfuse_callback: Any | None = None,
) -> _GraphLaneExecutionResult:
    lane_callbacks, lane_langfuse_callback = _build_callbacks(
        external_callbacks=callbacks,
        external_langfuse_callback=langfuse_callback,
        sampling_key=run_metadata.run_id,
    )
    logger.info(
        "Parallel graph lane start lane_index=%s lane_total=%s sub_question=%s run_id=%s",
        lane_index,
        lane_total,
        _truncate_query(sub_question),
        run_metadata.run_id,
    )
    try:
        if runtime_execution_config.query_expansion_enabled:
            expand_output = run_expand_node(
                node_input=ExpandNodeInput(
                    main_question=main_question,
                    sub_question=sub_question,
                    run_metadata=run_metadata,
                ),
                model=model,
                config=runtime_execution_config.query_expansion_config,
                callbacks=lane_callbacks,
            )
        else:
            expand_output = _build_query_expansion_bypass_output(sub_question=sub_question)
        search_output = run_search_node(
            node_input=SearchNodeInput(
                sub_question=sub_question,
                expanded_queries=list(expand_output.expanded_queries),
                run_metadata=run_metadata,
            ),
            vector_store=vector_store,
            k_fetch=_SEARCH_NODE_K_FETCH,
        )
        rerank_input = RerankNodeInput(
            sub_question=sub_question,
            expanded_query=_select_compat_expanded_query(
                sub_question=sub_question,
                expanded_queries=list(expand_output.expanded_queries),
            ),
            retrieved_docs=[row.model_copy(deep=True) for row in search_output.retrieved_docs],
            run_metadata=run_metadata,
        )
        if runtime_execution_config.rerank_config.enabled:
            rerank_output = run_rerank_node(
                node_input=rerank_input,
                config=runtime_execution_config.rerank_config,
                callbacks=lane_callbacks,
            )
        else:
            rerank_output = _build_rerank_bypass_output(node_input=rerank_input)
        answer_input_rows = rerank_output.reranked_docs or search_output.retrieved_docs
        answer_citation_rows = rerank_output.citation_rows_by_index or search_output.citation_rows_by_index
        answer_output = run_answer_subquestion_node(
            node_input=AnswerSubquestionNodeInput(
                sub_question=sub_question,
                reranked_docs=[row.model_copy(deep=True) for row in answer_input_rows],
                citation_rows_by_index={
                    key: value.model_copy(deep=True) for key, value in answer_citation_rows.items()
                },
                run_metadata=run_metadata,
            ),
            prompt_template=runtime_execution_config.subanswer_prompt,
            callbacks=lane_callbacks,
        )
    finally:
        if langfuse_callback is None:
            flush_langfuse_callback_handler(lane_langfuse_callback)
    logger.info(
        "Parallel graph lane complete lane_index=%s lane_total=%s sub_question=%s answerable=%s run_id=%s",
        lane_index,
        lane_total,
        _truncate_query(sub_question),
        answer_output.answerable,
        run_metadata.run_id,
    )
    return _GraphLaneExecutionResult(
        lane_index=lane_index,
        lane_total=lane_total,
        sub_question=sub_question,
        expand_output=expand_output,
        search_output=search_output,
        rerank_output=rerank_output,
        answer_output=answer_output,
    )


def run_parallel_graph_runner(
    *,
    payload: RuntimeAgentRunRequest,
    vector_store: Any,
    model: BaseChatModel | None = None,
    run_metadata: GraphRunMetadata | None = None,
    initial_search_context: list[dict[str, Any]] | None = None,
    snapshot_callback: Any | None = None,
    callbacks: list[Any] | None = None,
    langfuse_callback: Any | None = None,
) -> AgentGraphState:
    resolved_run_metadata = run_metadata or build_graph_run_metadata()
    resolved_initial_search_context = list(initial_search_context or [])
    resolved_runtime_execution_config = _resolve_runtime_execution_config(payload)
    state = build_agent_graph_state(
        main_question=payload.query,
        decomposition_sub_questions=[],
        sub_qa=[],
        final_answer="",
        run_metadata=resolved_run_metadata,
    )
    resolved_callbacks, resolved_langfuse_callback = _build_callbacks(
        external_callbacks=callbacks,
        external_langfuse_callback=langfuse_callback,
        sampling_key=resolved_run_metadata.run_id,
    )
    logger.info(
        "Parallel graph runner start query=%s callback_count=%s langfuse_enabled=%s configured_max_workers=%s run_id=%s trace_id=%s correlation_id=%s",
        _truncate_query(payload.query),
        len(resolved_callbacks),
        resolved_langfuse_callback is not None,
        _GRAPH_RUNNER_MAX_WORKERS,
        resolved_run_metadata.run_id,
        resolved_run_metadata.trace_id,
        resolved_run_metadata.correlation_id,
    )
    try:
        decomposition_output = run_decomposition_node(
            node_input=DecomposeNodeInput(
                main_question=payload.query,
                run_metadata=resolved_run_metadata,
                initial_search_context=resolved_initial_search_context,
            ),
            model=model,
            timeout_s=_RUNTIME_TIMEOUT_CONFIG.decomposition_llm_timeout_s,
            callbacks=resolved_callbacks,
        )
        state = apply_decompose_node_output_to_graph_state(
            state=state,
            node_output=decomposition_output,
        )
        _emit_graph_state_snapshot(
            state=state,
            stage="decompose",
            snapshot_callback=snapshot_callback,
        )

        lane_total = len(state.decomposition_sub_questions)
        ordered_lane_results: list[_GraphLaneExecutionResult | None] = [None] * lane_total
        if lane_total:
            effective_workers = min(_GRAPH_RUNNER_MAX_WORKERS, lane_total)
            logger.info(
                "Parallel graph runner fanout start lane_total=%s effective_workers=%s run_id=%s",
                lane_total,
                effective_workers,
                state.run_metadata.run_id,
            )
            with ThreadPoolExecutor(max_workers=effective_workers) as executor:
                future_by_lane_index = {
                    executor.submit(
                        _run_graph_subquestion_lane,
                        main_question=payload.query,
                        sub_question=sub_question,
                        lane_index=lane_index,
                        lane_total=lane_total,
                        vector_store=vector_store,
                        model=model,
                        run_metadata=state.run_metadata,
                        runtime_execution_config=resolved_runtime_execution_config,
                        callbacks=callbacks,
                        langfuse_callback=langfuse_callback,
                    ): lane_index
                    for lane_index, sub_question in enumerate(state.decomposition_sub_questions, start=1)
                }
                for future in as_completed(future_by_lane_index):
                    lane_index = future_by_lane_index[future]
                    lane_result = future.result()
                    ordered_lane_results[lane_index - 1] = lane_result
                    logger.info(
                        "Parallel graph runner fanout lane completed lane_index=%s lane_total=%s sub_question=%s run_id=%s",
                        lane_result.lane_index,
                        lane_result.lane_total,
                        _truncate_query(lane_result.sub_question),
                        state.run_metadata.run_id,
                    )

        for lane_result in ordered_lane_results:
            if lane_result is None:
                continue
            state = apply_expand_node_output_to_graph_state(
                state=state,
                sub_question=lane_result.sub_question,
                node_output=lane_result.expand_output,
            )
            _emit_graph_state_snapshot(
                state=state,
                stage="expand",
                sub_question=lane_result.sub_question,
                lane_index=lane_result.lane_index,
                lane_total=lane_result.lane_total,
                snapshot_callback=snapshot_callback,
            )
            state = apply_search_node_output_to_graph_state(
                state=state,
                sub_question=lane_result.sub_question,
                node_output=lane_result.search_output,
            )
            _emit_graph_state_snapshot(
                state=state,
                stage="search",
                sub_question=lane_result.sub_question,
                lane_index=lane_result.lane_index,
                lane_total=lane_result.lane_total,
                snapshot_callback=snapshot_callback,
            )
            state = apply_rerank_node_output_to_graph_state(
                state=state,
                sub_question=lane_result.sub_question,
                node_output=lane_result.rerank_output,
            )
            _emit_graph_state_snapshot(
                state=state,
                stage="rerank",
                sub_question=lane_result.sub_question,
                lane_index=lane_result.lane_index,
                lane_total=lane_result.lane_total,
                snapshot_callback=snapshot_callback,
            )
            state = apply_answer_subquestion_node_output_to_graph_state(
                state=state,
                sub_question=lane_result.sub_question,
                node_output=lane_result.answer_output,
            )
            _emit_graph_state_snapshot(
                state=state,
                stage="answer",
                sub_question=lane_result.sub_question,
                lane_index=lane_result.lane_index,
                lane_total=lane_result.lane_total,
                snapshot_callback=snapshot_callback,
            )

        synthesis_output = run_synthesize_final_node(
            node_input=SynthesizeFinalNodeInput(
                main_question=payload.query,
                sub_qa=[item.model_copy(deep=True) for item in state.sub_qa],
                sub_question_artifacts=[item.model_copy(deep=True) for item in state.sub_question_artifacts],
                run_metadata=state.run_metadata,
            ),
            prompt_template=resolved_runtime_execution_config.synthesis_prompt,
            callbacks=resolved_callbacks,
        )
        state = apply_synthesize_final_node_output_to_graph_state(
            state=state,
            node_output=synthesis_output,
        )
        _emit_graph_state_snapshot(
            state=state,
            stage="synthesize_final",
            snapshot_callback=snapshot_callback,
        )
        logger.info(
            "Parallel graph runner complete sub_question_count=%s output_len=%s snapshot_count=%s run_id=%s",
            len(state.sub_qa),
            len(state.output),
            len(state.stage_snapshots),
            state.run_metadata.run_id,
        )
        return state
    finally:
        if langfuse_callback is None:
            flush_langfuse_callback_handler(resolved_langfuse_callback)


def run_sequential_graph_runner(
    *,
    payload: RuntimeAgentRunRequest,
    vector_store: Any,
    model: BaseChatModel | None = None,
    run_metadata: GraphRunMetadata | None = None,
    initial_search_context: list[dict[str, Any]] | None = None,
    callbacks: list[Any] | None = None,
    langfuse_callback: Any | None = None,
) -> AgentGraphState:
    resolved_run_metadata = run_metadata or build_graph_run_metadata()
    resolved_initial_search_context = list(initial_search_context or [])
    resolved_runtime_execution_config = _resolve_runtime_execution_config(payload)
    state = build_agent_graph_state(
        main_question=payload.query,
        decomposition_sub_questions=[],
        sub_qa=[],
        final_answer="",
        run_metadata=resolved_run_metadata,
    )
    resolved_callbacks, resolved_langfuse_callback = _build_callbacks(
        external_callbacks=callbacks,
        external_langfuse_callback=langfuse_callback,
        sampling_key=resolved_run_metadata.run_id,
    )
    logger.info(
        "Sequential graph runner start query=%s callback_count=%s langfuse_enabled=%s run_id=%s trace_id=%s correlation_id=%s",
        _truncate_query(payload.query),
        len(resolved_callbacks),
        resolved_langfuse_callback is not None,
        resolved_run_metadata.run_id,
        resolved_run_metadata.trace_id,
        resolved_run_metadata.correlation_id,
    )
    try:
        decomposition_output = run_decomposition_node(
            node_input=DecomposeNodeInput(
                main_question=payload.query,
                run_metadata=resolved_run_metadata,
                initial_search_context=resolved_initial_search_context,
            ),
            model=model,
            timeout_s=_RUNTIME_TIMEOUT_CONFIG.decomposition_llm_timeout_s,
            callbacks=resolved_callbacks,
        )
        state = apply_decompose_node_output_to_graph_state(
            state=state,
            node_output=decomposition_output,
        )

        for index, sub_question in enumerate(state.decomposition_sub_questions, start=1):
            logger.info(
                "Sequential graph lane start lane_index=%s lane_total=%s sub_question=%s run_id=%s",
                index,
                len(state.decomposition_sub_questions),
                _truncate_query(sub_question),
                state.run_metadata.run_id,
            )
            if resolved_runtime_execution_config.query_expansion_enabled:
                expand_output = run_expand_node(
                    node_input=ExpandNodeInput(
                        main_question=payload.query,
                        sub_question=sub_question,
                        run_metadata=state.run_metadata,
                    ),
                    model=model,
                    config=resolved_runtime_execution_config.query_expansion_config,
                    callbacks=resolved_callbacks,
                )
            else:
                expand_output = _build_query_expansion_bypass_output(sub_question=sub_question)
            state = apply_expand_node_output_to_graph_state(
                state=state,
                sub_question=sub_question,
                node_output=expand_output,
            )

            search_output = run_search_node(
                node_input=SearchNodeInput(
                    sub_question=sub_question,
                    expanded_queries=list(expand_output.expanded_queries),
                    run_metadata=state.run_metadata,
                ),
                vector_store=vector_store,
                k_fetch=_SEARCH_NODE_K_FETCH,
            )
            state = apply_search_node_output_to_graph_state(
                state=state,
                sub_question=sub_question,
                node_output=search_output,
            )

            rerank_input = RerankNodeInput(
                sub_question=sub_question,
                expanded_query=_select_compat_expanded_query(
                    sub_question=sub_question,
                    expanded_queries=list(expand_output.expanded_queries),
                ),
                retrieved_docs=[row.model_copy(deep=True) for row in search_output.retrieved_docs],
                run_metadata=state.run_metadata,
            )
            if resolved_runtime_execution_config.rerank_config.enabled:
                rerank_output = run_rerank_node(
                    node_input=rerank_input,
                    config=resolved_runtime_execution_config.rerank_config,
                    callbacks=resolved_callbacks,
                )
            else:
                rerank_output = _build_rerank_bypass_output(node_input=rerank_input)
            state = apply_rerank_node_output_to_graph_state(
                state=state,
                sub_question=sub_question,
                node_output=rerank_output,
            )

            answer_input_rows = rerank_output.reranked_docs or search_output.retrieved_docs
            answer_citation_rows = rerank_output.citation_rows_by_index or search_output.citation_rows_by_index
            answer_output = run_answer_subquestion_node(
                node_input=AnswerSubquestionNodeInput(
                    sub_question=sub_question,
                    reranked_docs=[row.model_copy(deep=True) for row in answer_input_rows],
                    citation_rows_by_index={
                        key: value.model_copy(deep=True) for key, value in answer_citation_rows.items()
                    },
                    run_metadata=state.run_metadata,
                ),
                prompt_template=resolved_runtime_execution_config.subanswer_prompt,
                callbacks=resolved_callbacks,
            )
            state = apply_answer_subquestion_node_output_to_graph_state(
                state=state,
                sub_question=sub_question,
                node_output=answer_output,
            )
            logger.info(
                "Sequential graph lane complete lane_index=%s lane_total=%s sub_question=%s answerable=%s run_id=%s",
                index,
                len(state.decomposition_sub_questions),
                _truncate_query(sub_question),
                answer_output.answerable,
                state.run_metadata.run_id,
            )

        synthesis_output = run_synthesize_final_node(
            node_input=SynthesizeFinalNodeInput(
                main_question=payload.query,
                sub_qa=[item.model_copy(deep=True) for item in state.sub_qa],
                sub_question_artifacts=[item.model_copy(deep=True) for item in state.sub_question_artifacts],
                run_metadata=state.run_metadata,
            ),
            prompt_template=resolved_runtime_execution_config.synthesis_prompt,
            callbacks=resolved_callbacks,
        )
        state = apply_synthesize_final_node_output_to_graph_state(
            state=state,
            node_output=synthesis_output,
        )
        logger.info(
            "Sequential graph runner complete sub_question_count=%s output_len=%s run_id=%s",
            len(state.sub_qa),
            len(state.output),
            state.run_metadata.run_id,
        )
        return state
    finally:
        if langfuse_callback is None:
            flush_langfuse_callback_handler(resolved_langfuse_callback)


def run_decomposition_node(
    *,
    node_input: DecomposeNodeInput,
    model: BaseChatModel | None = None,
    timeout_s: int | None = None,
    callbacks: list[Any] | None = None,
) -> DecomposeNodeOutput:
    from agent_search.runtime.nodes.decompose import run_decomposition_node as run_runtime_decomposition_node

    return run_runtime_decomposition_node(
        node_input=node_input,
        model=model,
        timeout_s=timeout_s,
        callbacks=callbacks,
        run_llm_call_fn=_run_decomposition_only_llm_call,
        parse_output_fn=_parse_decomposition_output,
        normalize_sub_question_fn=_normalize_sub_question,
        truncate_query_fn=_truncate_query,
    )


def run_expand_node(
    *,
    node_input: ExpandNodeInput,
    model: BaseChatModel | None = None,
    config: QueryExpansionConfig | None = None,
    callbacks: list[Any] | None = None,
) -> ExpandNodeOutput:
    from agent_search.runtime.nodes.expand import run_expansion_node as run_runtime_expansion_node

    return run_runtime_expansion_node(
        node_input=node_input,
        model=model,
        config=config,
        callbacks=callbacks,
        default_config=_QUERY_EXPANSION_CONFIG,
        expand_queries_fn=expand_queries_for_subquestion,
        truncate_query_fn=_truncate_query,
    )


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
        "Per-subquestion pipeline parallel start count=%s configured_max_workers=%s effective_workers=%s total_timeout_ignored=%s",
        len(sub_qa),
        configured_workers,
        max_workers,
        total_timeout_s is not None,
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
        "Per-subquestion pipeline parallel complete count=%s total_timeout_ignored=%s",
        len(processed),
        total_timeout_s is not None,
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
    _ = db
    logger.info(
        "Runtime agent service wrapper delegating to runtime core query=%s query_length=%s provided_model=%s provided_vector_store=%s",
        _truncate_query(payload.query),
        len(payload.query),
        model is not None,
        vector_store is not None,
    )
    from agent_search.runtime.runner import run_runtime_agent as run_runtime_agent_core

    response = run_runtime_agent_core(
        payload,
        model=model,
        vector_store=vector_store,
    )
    logger.info(
        "Runtime agent service wrapper completed delegation sub_qa_count=%s output_length=%s",
        len(response.sub_items),
        len(response.output),
    )
    return response
