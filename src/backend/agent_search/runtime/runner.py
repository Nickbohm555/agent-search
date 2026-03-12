from __future__ import annotations

import logging
from typing import Any

from agent_search.errors import SDKConfigurationError
from schemas import RuntimeAgentRunRequest, RuntimeAgentRunResponse
from services import agent_service as legacy_service
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
    callbacks: list[Any] | None = None,
    langfuse_callback: Any | None = None,
) -> RuntimeAgentRunResponse:
    if model is None:
        logger.error("Runtime core run rejected missing model")
        raise SDKConfigurationError("model is required and cannot be None")
    if vector_store is None:
        logger.error("Runtime core run rejected missing vector_store")
        raise SDKConfigurationError("vector_store is required and cannot be None")
    run_metadata = legacy_service.build_graph_run_metadata(thread_id=payload.thread_id)
    runtime_trace = None
    if langfuse_callback is not None:
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
    selected_vector_store = vector_store
    logger.info(
        "Runtime core vector store selected source=provided run_id=%s",
        run_metadata.run_id,
    )
    initial_search_context: list[dict[str, Any]] = []
    logger.info(
        "Runtime core initial context retrieval disabled; proceeding with empty context run_id=%s",
        run_metadata.run_id,
    )

    state = legacy_service.run_parallel_graph_runner(
        payload=payload,
        vector_store=selected_vector_store,
        model=model,
        run_metadata=run_metadata,
        initial_search_context=initial_search_context,
        callbacks=callbacks,
        langfuse_callback=langfuse_callback,
    )
    if runtime_trace is not None:
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
    if runtime_trace is not None:
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
