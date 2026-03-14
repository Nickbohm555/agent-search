from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy, interrupt

from agent_search.runtime.graph.routes import route_post_decompose, route_subquestion_lanes
from agent_search.runtime.graph.state import RuntimeGraphContext, RuntimeGraphState
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


def _attach_checkpoint_metadata(interrupt_payload: Any, *, checkpoint_id: str | None = None) -> Any:
    if not isinstance(interrupt_payload, Mapping):
        return interrupt_payload
    normalized_payload = dict(interrupt_payload)
    if checkpoint_id and not normalized_payload.get("checkpoint_id"):
        normalized_payload["checkpoint_id"] = checkpoint_id
    return normalized_payload


def _apply_subquestion_resume_decisions(
    subquestions: Sequence[str],
    *,
    resume: Any = True,
    interrupt_payload: Any | None = None,
) -> list[str]:
    baseline_subquestions = [str(subquestion) for subquestion in subquestions]
    if not hasattr(resume, "decisions"):
        return baseline_subquestions

    available_ids = [f"sq-{index + 1}" for index in range(len(baseline_subquestions))]
    if isinstance(interrupt_payload, Mapping):
        raw_items = interrupt_payload.get("subquestions")
        if isinstance(raw_items, Sequence) and not isinstance(raw_items, (str, bytes, bytearray)):
            available_ids = []
            for fallback_index, raw_item in enumerate(raw_items):
                if not isinstance(raw_item, Mapping):
                    available_ids.append(f"sq-{fallback_index + 1}")
                    continue
                raw_id = raw_item.get("subquestion_id")
                available_ids.append(str(raw_id or f"sq-{fallback_index + 1}"))

    decisions_by_id = {str(decision.subquestion_id): decision for decision in resume.decisions}
    resolved_subquestions: list[str] = []
    for index, current_text in enumerate(baseline_subquestions):
        decision = decisions_by_id.get(available_ids[index] if index < len(available_ids) else f"sq-{index + 1}")
        if decision is None or decision.action in {"approve", "skip"}:
            resolved_subquestions.append(current_text)
            continue
        if decision.action == "edit":
            edited_text = str(decision.edited_text or "").strip()
            if edited_text:
                resolved_subquestions.append(edited_text)
            continue
        if decision.action == "deny":
            continue
        raise ValueError(f"Unsupported resume action '{decision.action}'.")
    return resolved_subquestions


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
        initial_search_context=list(state.get("initial_search_context", [])),
        subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
        query_expansion_hitl_enabled=bool(state.get("query_expansion_hitl_enabled", False)),
    )


def _with_runtime_context(state: RuntimeGraphState, next_state: dict[str, Any]) -> RuntimeGraphState:
    return RuntimeGraphState(
        **next_state,
        initial_search_context=list(state.get("initial_search_context", [])),
        subquestion_hitl_enabled=bool(state.get("subquestion_hitl_enabled", False)),
        query_expansion_hitl_enabled=bool(state.get("query_expansion_hitl_enabled", False)),
    )


def _resolve_lane_sub_question(state: RuntimeGraphState) -> str:
    if not state["decomposition_sub_questions"]:
        raise ValueError("Lane state must contain exactly one decomposition sub-question.")
    return state["decomposition_sub_questions"][0]


def _build_decompose_node(context: RuntimeGraphContext):
    def _decompose(state: RuntimeGraphState) -> RuntimeGraphState:
        node_output = legacy_service.run_decomposition_node(
            node_input=DecomposeNodeInput(
                main_question=state["main_question"],
                run_metadata=state["run_metadata"],
                initial_search_context=list(state.get("initial_search_context", [])),
            ),
            model=context.model,
            timeout_s=legacy_service._RUNTIME_TIMEOUT_CONFIG.decomposition_llm_timeout_s,
            callbacks=context.callbacks,
        )
        next_state = legacy_service.apply_decompose_node_output_to_graph_state(state=state, node_output=node_output)
        return _append_snapshot(_with_runtime_context(state, to_rag_state(next_state)), stage="decompose")

    return _decompose


def _build_subquestion_checkpoint_node():
    def _subquestion_checkpoint(state: RuntimeGraphState) -> RuntimeGraphState:
        if not state["subquestion_hitl_enabled"] or not state["decomposition_sub_questions"]:
            return state
        interrupt_payload = _attach_checkpoint_metadata(
            {
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
        )
        resume_value = interrupt(interrupt_payload)
        next_state = to_rag_state(state)
        next_state["decomposition_sub_questions"] = _apply_subquestion_resume_decisions(
            state["decomposition_sub_questions"],
            resume=resume_value,
            interrupt_payload=interrupt_payload,
        )
        return _with_runtime_context(state, next_state)

    return _subquestion_checkpoint


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
        return _append_snapshot(_with_runtime_context(state, to_rag_state(next_state)), stage="expand", sub_question=sub_question)

    return _expand


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
        return _append_snapshot(_with_runtime_context(state, to_rag_state(next_state)), stage="search", sub_question=sub_question)

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
        return _append_snapshot(_with_runtime_context(state, to_rag_state(next_state)), stage="rerank", sub_question=sub_question)

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
        return _append_snapshot(_with_runtime_context(state, to_rag_state(next_state)), stage="answer", sub_question=sub_question)

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
        return _append_snapshot(_with_runtime_context(state, to_rag_state(next_state)), stage="synthesize_final")

    return _synthesize


def build_runtime_graph(
    *,
    context: RuntimeGraphContext | None = None,
    **compile_kwargs: Any,
) -> Any:
    resolved_context = context or RuntimeGraphContext(payload=RuntimeAgentRunRequest(query="bootstrap"))
    builder = StateGraph(RuntimeGraphState)
    builder.add_node("decompose", _build_decompose_node(resolved_context))
    builder.add_node("subquestion_checkpoint", _build_subquestion_checkpoint_node())
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
    builder.add_edge("expand", "search")
    builder.add_edge("search", "rerank")
    builder.add_edge("rerank", "answer")
    builder.add_edge("answer", "synthesize")
    builder.add_edge("synthesize", END)
    return builder.compile(**compile_kwargs)


__all__ = ["build_runtime_graph"]
