from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, interrupt

from agent_search.runtime.graph.routes import route_post_decompose, route_subquestion_lanes
from agent_search.runtime.graph.state import RuntimeGraphContext, RuntimeGraphState
from agent_search.runtime.resume import (
    apply_subquestion_resume_decisions,
    attach_checkpoint_metadata,
)
from agent_search.runtime.reducers import merge_stage_snapshots
from agent_search.runtime.state import to_rag_state
from schemas import (
    AnswerSubquestionNodeInput,
    DecomposeNodeInput,
    ExpandNodeInput,
    GraphStageSnapshot,
    RerankNodeInput,
    RuntimeAgentRunRequest,
    SearchNodeInput,
    SubQuestionArtifacts,
    SynthesizeFinalNodeInput,
)
from services import agent_service as legacy_service

_RETRY_POLICY = RetryPolicy(max_attempts=3)


def _append_snapshot(
    state: RuntimeGraphState,
    *,
    stage: str,
    sub_question: str = "",
) -> RuntimeGraphState:
    next_state = to_rag_state(state)
    next_state["stage_snapshots"] = merge_stage_snapshots(
        next_state["stage_snapshots"],
        [
            GraphStageSnapshot(
                stage=stage,
                status="completed",
                sub_question=sub_question,
                decomposition_sub_questions=list(next_state["decomposition_sub_questions"]),
                sub_qa=[item.model_copy(deep=True) for item in next_state["sub_qa"]],
                sub_question_artifacts=[item.model_copy(deep=True) for item in next_state["sub_question_artifacts"]],
                output=next_state["output"],
            )
        ],
    )
    return RuntimeGraphState(
        **next_state,
        lane_sub_question=str(state.get("lane_sub_question", "")),
        initial_search_context=list(state.get("initial_search_context", [])),
        subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
    )


def _resolve_lane_sub_question(state: RuntimeGraphState) -> str:
    lane_sub_question = str(state.get("lane_sub_question", "")).strip()
    if lane_sub_question:
        return lane_sub_question
    if len(state["decomposition_sub_questions"]) == 1:
        return state["decomposition_sub_questions"][0]
    raise ValueError("Lane state must contain a lane_sub_question before lane execution.")


def _build_decompose_node(context: RuntimeGraphContext):
    def _decompose(state: RuntimeGraphState) -> RuntimeGraphState:
        node_output = legacy_service.run_decomposition_node(
            node_input=DecomposeNodeInput(
                main_question=state["main_question"],
                run_metadata=state["run_metadata"],
                initial_search_context=list(state.get("initial_search_context", [])),
            ),
            model=context.model,
            callbacks=context.callbacks,
        )
        next_state = legacy_service.apply_decompose_node_output_to_graph_state(state=state, node_output=node_output)
        return _append_snapshot(
            RuntimeGraphState(
                **to_rag_state(next_state),
                lane_sub_question=str(state.get("lane_sub_question", "")),
                initial_search_context=list(state.get("initial_search_context", [])),
                subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
            ),
            stage="decompose",
        )

    return _decompose


def _build_expand_node(context: RuntimeGraphContext):
    def _expand(state: RuntimeGraphState) -> RuntimeGraphState:
        sub_question = _resolve_lane_sub_question(state)
        node_output = legacy_service.run_expand_node(
            node_input=ExpandNodeInput(
                main_question=state["main_question"],
                sub_question=sub_question,
                run_metadata=state["run_metadata"],
            ),
            model=context.model,
            callbacks=context.callbacks,
        )
        next_state = legacy_service.apply_expand_node_output_to_graph_state(
            state=state,
            sub_question=sub_question,
            node_output=node_output,
        )
        return _append_snapshot(
            RuntimeGraphState(
                **to_rag_state(next_state),
                lane_sub_question=str(state.get("lane_sub_question", "")),
                initial_search_context=list(state.get("initial_search_context", [])),
                subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
            ),
            stage="expand",
            sub_question=sub_question,
        )

    return _expand


def _build_subquestion_checkpoint_node():
    def _subquestion_checkpoint(state: RuntimeGraphState) -> RuntimeGraphState:
        if not state["subquestion_hitl_enabled"] or not state["decomposition_sub_questions"]:
            return state
        interrupt_payload = attach_checkpoint_metadata(
            {
                "thread_id": state["run_metadata"].thread_id,
                "checkpoint_id": state["run_metadata"].thread_id,
                "kind": "subquestion_review",
                "stage": "subquestions_ready",
                "subquestions": [
                    {
                        "subquestion_id": f"sq-{index + 1}",
                        "sub_question": sub_question,
                        "index": index,
                    }
                    for index, sub_question in enumerate(state["decomposition_sub_questions"])
                ],
            },
            checkpoint_id=state["run_metadata"].thread_id,
            thread_id=state["run_metadata"].thread_id,
        )
        resume_value = interrupt(interrupt_payload)
        next_state = to_rag_state(state)
        next_state["decomposition_sub_questions"] = apply_subquestion_resume_decisions(
            state["decomposition_sub_questions"],
            resume=resume_value,
            interrupt_payload=interrupt_payload,
        )
        return RuntimeGraphState(
            **next_state,
            lane_sub_question=str(state.get("lane_sub_question", "")),
            initial_search_context=list(state.get("initial_search_context", [])),
            subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
        )

    return _subquestion_checkpoint


def _build_search_node(context: RuntimeGraphContext):
    def _search(state: RuntimeGraphState) -> RuntimeGraphState:
        sub_question = _resolve_lane_sub_question(state)
        artifact = next(
            (item for item in state["sub_question_artifacts"] if item.sub_question == sub_question),
            SubQuestionArtifacts(sub_question=sub_question),
        )
        node_output = legacy_service.run_search_node(
            node_input=SearchNodeInput(
                sub_question=sub_question,
                expanded_queries=list(artifact.expanded_queries),
                run_metadata=state["run_metadata"],
            ),
            vector_store=context.vector_store,
            k_fetch=legacy_service._SEARCH_NODE_K_FETCH,
        )
        next_state = legacy_service.apply_search_node_output_to_graph_state(
            state=state,
            sub_question=sub_question,
            node_output=node_output,
        )
        return _append_snapshot(
            RuntimeGraphState(
                **to_rag_state(next_state),
                lane_sub_question=str(state.get("lane_sub_question", "")),
                initial_search_context=list(state.get("initial_search_context", [])),
                subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
            ),
            stage="search",
            sub_question=sub_question,
        )

    return _search


def _build_rerank_node(context: RuntimeGraphContext):
    def _rerank(state: RuntimeGraphState) -> RuntimeGraphState:
        sub_question = _resolve_lane_sub_question(state)
        artifact = next(
            (item for item in state["sub_question_artifacts"] if item.sub_question == sub_question),
            SubQuestionArtifacts(sub_question=sub_question),
        )
        node_output = legacy_service.run_rerank_node(
            node_input=RerankNodeInput(
                sub_question=sub_question,
                expanded_query=legacy_service._select_compat_expanded_query(
                    sub_question=sub_question,
                    expanded_queries=list(artifact.expanded_queries),
                ),
                retrieved_docs=[row.model_copy(deep=True) for row in artifact.retrieved_docs],
                run_metadata=state["run_metadata"],
            ),
            config=legacy_service._RERANKER_CONFIG,
            callbacks=context.callbacks,
        )
        next_state = legacy_service.apply_rerank_node_output_to_graph_state(
            state=state,
            sub_question=sub_question,
            node_output=node_output,
        )
        return _append_snapshot(
            RuntimeGraphState(
                **to_rag_state(next_state),
                lane_sub_question=str(state.get("lane_sub_question", "")),
                initial_search_context=list(state.get("initial_search_context", [])),
                subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
            ),
            stage="rerank",
            sub_question=sub_question,
        )

    return _rerank


def _build_answer_node(context: RuntimeGraphContext):
    def _answer(state: RuntimeGraphState) -> RuntimeGraphState:
        sub_question = _resolve_lane_sub_question(state)
        artifact = next(
            (item for item in state["sub_question_artifacts"] if item.sub_question == sub_question),
            SubQuestionArtifacts(sub_question=sub_question),
        )
        answer_rows = artifact.reranked_docs or artifact.retrieved_docs
        answer_citation_rows = artifact.citation_rows_by_index
        node_output = legacy_service.run_answer_subquestion_node(
            node_input=AnswerSubquestionNodeInput(
                sub_question=sub_question,
                reranked_docs=[row.model_copy(deep=True) for row in answer_rows],
                citation_rows_by_index={
                    key: value.model_copy(deep=True) for key, value in answer_citation_rows.items()
                },
                run_metadata=state["run_metadata"],
            ),
            callbacks=context.callbacks,
        )
        next_state = legacy_service.apply_answer_subquestion_node_output_to_graph_state(
            state=state,
            sub_question=sub_question,
            node_output=node_output,
        )
        return _append_snapshot(
            RuntimeGraphState(
                **to_rag_state(next_state),
                lane_sub_question=str(state.get("lane_sub_question", "")),
                initial_search_context=list(state.get("initial_search_context", [])),
                subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
            ),
            stage="answer",
            sub_question=sub_question,
        )

    return _answer


def _build_synthesize_node(context: RuntimeGraphContext):
    def _synthesize(state: RuntimeGraphState) -> RuntimeGraphState:
        node_output = legacy_service.run_synthesize_final_node(
            node_input=SynthesizeFinalNodeInput(
                main_question=state["main_question"],
                sub_qa=[item.model_copy(deep=True) for item in state["sub_qa"]],
                sub_question_artifacts=[item.model_copy(deep=True) for item in state["sub_question_artifacts"]],
                run_metadata=state["run_metadata"],
            ),
            callbacks=context.callbacks,
        )
        next_state = legacy_service.apply_synthesize_final_node_output_to_graph_state(
            state=state,
            node_output=node_output,
        )
        return _append_snapshot(
            RuntimeGraphState(
                **to_rag_state(next_state),
                lane_sub_question=str(state.get("lane_sub_question", "")),
                initial_search_context=list(state.get("initial_search_context", [])),
                subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
            ),
            stage="synthesize_final",
        )

    return _synthesize


def _build_lane_pipeline_node(context: RuntimeGraphContext):
    def _lane_pipeline(state: RuntimeGraphState) -> RuntimeGraphState:
        sub_question = _resolve_lane_sub_question(state)

        expand_output = legacy_service.run_expand_node(
            node_input=ExpandNodeInput(
                main_question=state["main_question"],
                sub_question=sub_question,
                run_metadata=state["run_metadata"],
            ),
            model=context.model,
            callbacks=context.callbacks,
        )
        next_state = legacy_service.apply_expand_node_output_to_graph_state(
            state=state,
            sub_question=sub_question,
            node_output=expand_output,
        )
        lane_state = _append_snapshot(
            RuntimeGraphState(
                **to_rag_state(next_state),
                lane_sub_question=str(state.get("lane_sub_question", "")),
                initial_search_context=list(state.get("initial_search_context", [])),
                subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
            ),
            stage="expand",
            sub_question=sub_question,
        )

        artifact = next(
            (item for item in lane_state["sub_question_artifacts"] if item.sub_question == sub_question),
            SubQuestionArtifacts(sub_question=sub_question),
        )
        search_output = legacy_service.run_search_node(
            node_input=SearchNodeInput(
                sub_question=sub_question,
                expanded_queries=list(artifact.expanded_queries),
                run_metadata=lane_state["run_metadata"],
            ),
            vector_store=context.vector_store,
            k_fetch=legacy_service._SEARCH_NODE_K_FETCH,
        )
        next_state = legacy_service.apply_search_node_output_to_graph_state(
            state=lane_state,
            sub_question=sub_question,
            node_output=search_output,
        )
        lane_state = _append_snapshot(
            RuntimeGraphState(
                **to_rag_state(next_state),
                lane_sub_question=str(state.get("lane_sub_question", "")),
                initial_search_context=list(state.get("initial_search_context", [])),
                subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
            ),
            stage="search",
            sub_question=sub_question,
        )

        artifact = next(
            (item for item in lane_state["sub_question_artifacts"] if item.sub_question == sub_question),
            SubQuestionArtifacts(sub_question=sub_question),
        )
        rerank_output = legacy_service.run_rerank_node(
            node_input=RerankNodeInput(
                sub_question=sub_question,
                expanded_query=legacy_service._select_compat_expanded_query(
                    sub_question=sub_question,
                    expanded_queries=list(artifact.expanded_queries),
                ),
                retrieved_docs=[row.model_copy(deep=True) for row in artifact.retrieved_docs],
                run_metadata=lane_state["run_metadata"],
            ),
            config=legacy_service._RERANKER_CONFIG,
            callbacks=context.callbacks,
        )
        next_state = legacy_service.apply_rerank_node_output_to_graph_state(
            state=lane_state,
            sub_question=sub_question,
            node_output=rerank_output,
        )
        lane_state = _append_snapshot(
            RuntimeGraphState(
                **to_rag_state(next_state),
                lane_sub_question=str(state.get("lane_sub_question", "")),
                initial_search_context=list(state.get("initial_search_context", [])),
                subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
            ),
            stage="rerank",
            sub_question=sub_question,
        )

        artifact = next(
            (item for item in lane_state["sub_question_artifacts"] if item.sub_question == sub_question),
            SubQuestionArtifacts(sub_question=sub_question),
        )
        answer_rows = artifact.reranked_docs or artifact.retrieved_docs
        answer_output = legacy_service.run_answer_subquestion_node(
            node_input=AnswerSubquestionNodeInput(
                sub_question=sub_question,
                reranked_docs=[row.model_copy(deep=True) for row in answer_rows],
                citation_rows_by_index={
                    key: value.model_copy(deep=True) for key, value in artifact.citation_rows_by_index.items()
                },
                run_metadata=lane_state["run_metadata"],
            ),
            callbacks=context.callbacks,
        )
        next_state = legacy_service.apply_answer_subquestion_node_output_to_graph_state(
            state=lane_state,
            sub_question=sub_question,
            node_output=answer_output,
        )
        return _append_snapshot(
            RuntimeGraphState(
                **to_rag_state(next_state),
                lane_sub_question=str(state.get("lane_sub_question", "")),
                initial_search_context=list(state.get("initial_search_context", [])),
                subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
            ),
            stage="answer",
            sub_question=sub_question,
        )

    return _lane_pipeline


def build_runtime_graph(
    *,
    context: RuntimeGraphContext | None = None,
    **compile_kwargs: Any,
) -> Any:
    resolved_context = context or RuntimeGraphContext(payload=RuntimeAgentRunRequest(query="bootstrap"))
    builder = StateGraph(RuntimeGraphState)
    builder.add_node("decompose", _build_decompose_node(resolved_context))
    builder.add_node("subquestion_checkpoint", _build_subquestion_checkpoint_node())
    builder.add_node("lane_pipeline", _build_lane_pipeline_node(resolved_context), retry_policy=_RETRY_POLICY)
    builder.add_node("expand", _build_expand_node(resolved_context))
    builder.add_node("search", _build_search_node(resolved_context), retry_policy=_RETRY_POLICY)
    builder.add_node("rerank", _build_rerank_node(resolved_context), retry_policy=_RETRY_POLICY)
    builder.add_node("answer", _build_answer_node(resolved_context), retry_policy=_RETRY_POLICY)
    builder.add_node("synthesize", _build_synthesize_node(resolved_context), retry_policy=_RETRY_POLICY)
    builder.add_edge(START, "decompose")
    builder.add_conditional_edges(
        "decompose",
        route_post_decompose,
        {"synthesize": "synthesize", "subquestion_checkpoint": "subquestion_checkpoint"},
    )
    builder.add_conditional_edges("subquestion_checkpoint", route_subquestion_lanes)
    builder.add_edge("lane_pipeline", "synthesize")
    builder.add_edge("expand", "search")
    builder.add_edge("search", "rerank")
    builder.add_edge("rerank", "answer")
    builder.add_edge("answer", "synthesize")
    builder.add_edge("synthesize", END)
    return builder.compile(**compile_kwargs)


__all__ = ["build_runtime_graph"]
