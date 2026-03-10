from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeoutError
import logging
from typing import Any

from agent_search.errors import SDKConfigurationError
from schemas import RuntimeAgentRunRequest, RuntimeAgentRunResponse
from services import agent_service as legacy_service
from services.vector_store_service import (
    build_initial_search_context,
    search_documents_for_context,
)
from utils.langfuse_tracing import (
    end_langfuse_observation,
    record_langfuse_score,
    start_langfuse_span,
    start_langfuse_trace,
)

logger = logging.getLogger(__name__)


def run_runtime_agent(
    payload: RuntimeAgentRunRequest,
    *,
    model: Any | None = None,
    vector_store: Any | None = None,
) -> RuntimeAgentRunResponse:
    if model is None:
        logger.error("Runtime core run rejected missing model")
        raise SDKConfigurationError("model is required and cannot be None")
    if vector_store is None:
        logger.error("Runtime core run rejected missing vector_store")
        raise SDKConfigurationError("vector_store is required and cannot be None")
    run_metadata = legacy_service.build_graph_run_metadata()
    runtime_trace = start_langfuse_trace(
        name="runtime.agent_run",
        scope="runtime",
        sampling_key=run_metadata.run_id,
        trace_id=run_metadata.trace_id,
        session_id=run_metadata.thread_id,
        input_payload={"query": payload.query},
        metadata={
            "run_id": run_metadata.run_id,
            "trace_id": run_metadata.trace_id,
            "correlation_id": run_metadata.correlation_id,
        },
    )
    logger.info(
        "Runtime core run start query=%s query_length=%s provided_model=%s provided_vector_store=%s run_id=%s trace_id=%s correlation_id=%s",
        legacy_service._truncate_query(payload.query),
        len(payload.query),
        model is not None,
        vector_store is not None,
        run_metadata.run_id,
        run_metadata.trace_id,
        run_metadata.correlation_id,
    )
    initial_context_span = start_langfuse_span(
        parent=runtime_trace,
        name="runtime.initial_context",
        input_payload={"query": payload.query},
        metadata={"run_id": run_metadata.run_id},
    )
    selected_vector_store = vector_store
    logger.info(
        "Runtime core vector store selected source=provided run_id=%s",
        run_metadata.run_id,
    )

    def _build_initial_context_payload() -> tuple[list[Any], list[dict[str, Any]]]:
        docs = search_documents_for_context(
            vector_store=selected_vector_store,
            query=payload.query,
            k=legacy_service._INITIAL_SEARCH_CONTEXT_K,
            score_threshold=legacy_service._INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD,
        )
        return docs, build_initial_search_context(docs)

    try:
        _, initial_search_context = legacy_service._run_with_timeout(
            timeout_s=legacy_service._RUNTIME_TIMEOUT_CONFIG.initial_search_timeout_s,
            operation_name="initial_search_context_build",
            fn=_build_initial_context_payload,
        )
        logger.info(
            "Runtime core initial context built query=%s docs=%s k=%s score_threshold=%s run_id=%s",
            legacy_service._truncate_query(payload.query),
            len(initial_search_context),
            legacy_service._INITIAL_SEARCH_CONTEXT_K,
            legacy_service._INITIAL_SEARCH_CONTEXT_SCORE_THRESHOLD,
            run_metadata.run_id,
        )
    except FuturesTimeoutError:
        initial_search_context = []
        logger.warning(
            "Runtime core initial context timeout; continuing with empty context query=%s timeout_s=%s run_id=%s",
            legacy_service._truncate_query(payload.query),
            legacy_service._RUNTIME_TIMEOUT_CONFIG.initial_search_timeout_s,
            run_metadata.run_id,
        )
    finally:
        end_langfuse_observation(
            initial_context_span,
            output_payload={"context_document_count": len(initial_search_context)},
            metadata={"run_id": run_metadata.run_id},
        )

    state = legacy_service.run_parallel_graph_runner(
        payload=payload,
        vector_store=selected_vector_store,
        model=model,
        run_metadata=run_metadata,
        initial_search_context=initial_search_context,
    )
    for snapshot_index, snapshot in enumerate(state.stage_snapshots, start=1):
        stage_name = "final" if snapshot.stage == "synthesize_final" else snapshot.stage
        stage_span = start_langfuse_span(
            parent=runtime_trace,
            name=f"runtime.stage.{stage_name}",
            metadata={
                "run_id": run_metadata.run_id,
                "trace_id": run_metadata.trace_id,
                "correlation_id": run_metadata.correlation_id,
                "stage": snapshot.stage,
                "status": snapshot.status,
                "sub_question": snapshot.sub_question,
                "lane_index": snapshot.lane_index,
                "lane_total": snapshot.lane_total,
                "snapshot_index": snapshot_index,
            },
        )
        end_langfuse_observation(
            stage_span,
            output_payload={
                "decomposition_count": len(snapshot.decomposition_sub_questions),
                "sub_qa_count": len(snapshot.sub_qa),
                "output_length": len(snapshot.output or ""),
            },
        )
    response = legacy_service.map_graph_state_to_runtime_response(state)
    record_langfuse_score(
        parent=runtime_trace,
        name="runtime.sub_question_count",
        value=float(len(response.sub_qa)),
        metadata={"run_id": run_metadata.run_id},
    )
    end_langfuse_observation(
        runtime_trace,
        output_payload={
            "sub_qa_count": len(response.sub_qa),
            "output_length": len(response.output),
            "final_citation_count": len(response.final_citations),
            "snapshot_count": len(state.stage_snapshots),
        },
        metadata={"run_id": run_metadata.run_id},
    )
    logger.info(
        "Runtime core run complete sub_qa_count=%s output_length=%s snapshot_count=%s run_id=%s",
        len(response.sub_qa),
        len(response.output),
        len(state.stage_snapshots),
        run_metadata.run_id,
    )
    return response
