from __future__ import annotations

from concurrent.futures import TimeoutError as FuturesTimeoutError
import logging
from typing import Any

from db import DATABASE_URL
from schemas import RuntimeAgentRunRequest, RuntimeAgentRunResponse
from services import agent_service as legacy_service
from services.vector_store_service import (
    build_initial_search_context,
    get_vector_store,
    search_documents_for_context,
)
from utils.embeddings import get_embedding_model

logger = logging.getLogger(__name__)


def run_runtime_agent(
    payload: RuntimeAgentRunRequest,
    *,
    model: Any | None = None,
    vector_store: Any | None = None,
) -> RuntimeAgentRunResponse:
    run_metadata = legacy_service.build_graph_run_metadata()
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
    if selected_vector_store is None:
        try:
            selected_vector_store = legacy_service._run_with_timeout(
                timeout_s=legacy_service._RUNTIME_TIMEOUT_CONFIG.vector_store_acquisition_timeout_s,
                operation_name="vector_store_acquisition",
                fn=lambda: get_vector_store(
                    connection=DATABASE_URL,
                    collection_name=legacy_service._VECTOR_COLLECTION_NAME,
                    embeddings=get_embedding_model(),
                ),
            )
        except FuturesTimeoutError:
            logger.warning(
                "Runtime core short-circuiting due to vector store timeout query=%s run_id=%s",
                legacy_service._truncate_query(payload.query),
                run_metadata.run_id,
            )
            return RuntimeAgentRunResponse(
                main_question=payload.query,
                sub_qa=[],
                output=legacy_service._VECTOR_STORE_TIMEOUT_FALLBACK_MESSAGE,
            )
        logger.info(
            "Runtime core vector store selected source=default collection_name=%s run_id=%s",
            legacy_service._VECTOR_COLLECTION_NAME,
            run_metadata.run_id,
        )
    else:
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

    state = legacy_service.run_parallel_graph_runner(
        payload=payload,
        vector_store=selected_vector_store,
        model=model,
        run_metadata=run_metadata,
        initial_search_context=initial_search_context,
    )
    response = legacy_service.map_graph_state_to_runtime_response(state)
    logger.info(
        "Runtime core run complete sub_qa_count=%s output_length=%s snapshot_count=%s run_id=%s",
        len(response.sub_qa),
        len(response.output),
        len(state.stage_snapshots),
        run_metadata.run_id,
    )
    return response
