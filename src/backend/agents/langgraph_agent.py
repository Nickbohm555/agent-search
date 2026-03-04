from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypedDict

from langgraph.graph import END, START, StateGraph
from schemas import (
    RuntimeAgentGraphState,
    RuntimeAgentGraphStep,
    SubQueryExecutionResult,
    SubQueryRetrievalResult,
    SubQueryToolAssignment,
    SubQueryValidationResult,
)
from services.answer_synthesis_service import synthesize_answer
from services.retrieval_service import execute_subquery_retrieval
from services.validation_service import validate_retrieval_result
from sqlalchemy.orm import Session
from utils.query_decomposition import decompose_query
from utils.tool_selection import assign_tools_to_sub_queries


class SubQueryExecutionState(TypedDict):
    assignment: SubQueryToolAssignment
    db: Session
    retrieval_result: Optional[SubQueryRetrievalResult]
    validation_result: Optional[SubQueryValidationResult]


@dataclass
class SubQueryExecutionAgent:
    """Deep agent that owns retrieval + validation for one sub-query."""

    name: str = "subquery_execution_agent"
    _compiled_graph: Any = field(default=None, init=False, repr=False)

    def _build_graph(self) -> Any:
        graph = StateGraph(SubQueryExecutionState)
        graph.add_node("retrieval", self._retrieval_node)
        graph.add_node("validation", self._validation_node)
        graph.add_edge(START, "retrieval")
        graph.add_edge("retrieval", "validation")
        graph.add_edge("validation", END)
        return graph.compile()

    def _get_graph(self) -> Any:
        if self._compiled_graph is None:
            self._compiled_graph = self._build_graph()
        return self._compiled_graph

    @staticmethod
    def _retrieval_node(state: SubQueryExecutionState) -> SubQueryExecutionState:
        assignment = state["assignment"]
        retrieval = execute_subquery_retrieval(assignment, state["db"])
        return {"retrieval_result": retrieval}

    @staticmethod
    def _validation_node(state: SubQueryExecutionState) -> SubQueryExecutionState:
        retrieval_result = state["retrieval_result"]
        if retrieval_result is None:
            raise ValueError("SubQueryExecutionAgent validation requires retrieval_result.")
        validated_retrieval, validation_result = validate_retrieval_result(
            retrieval_result,
            state["db"],
        )
        return {
            "retrieval_result": validated_retrieval,
            "validation_result": validation_result,
        }

    def run(
        self,
        assignment: SubQueryToolAssignment,
        db: Session,
    ) -> tuple[SubQueryRetrievalResult, SubQueryValidationResult]:
        final_state = self._get_graph().invoke(
            {
                "assignment": assignment,
                "db": db,
                "retrieval_result": None,
                "validation_result": None,
            }
        )
        retrieval = final_state.get("retrieval_result")
        validation = final_state.get("validation_result")
        if retrieval is None or validation is None:
            raise ValueError("SubQueryExecutionAgent graph did not produce retrieval/validation.")
        return retrieval, validation


class RuntimeOrchestrationState(TypedDict):
    query: str
    db: Session
    sub_queries: list[str]
    tool_assignments: list[SubQueryToolAssignment]
    retrieval_results: list[SubQueryRetrievalResult]
    validation_results: list[SubQueryValidationResult]
    subquery_execution_results: list[SubQueryExecutionResult]
    output: str
    runtime_mode: str
    timeline: list[RuntimeAgentGraphStep]
    event_callback: Optional[Callable[[str, dict[str, Any]], None]]


@dataclass
class LangGraphAgentScaffold:
    """Runtime graph agent that orchestrates the full retrieval pipeline."""

    name: str
    model: str
    runtime_handle: Any | None = None
    subquery_agent: SubQueryExecutionAgent = field(default_factory=SubQueryExecutionAgent)
    _compiled_graph: Any = field(default=None, init=False, repr=False)

    def _build_graph(self) -> Any:
        graph = StateGraph(RuntimeOrchestrationState)
        graph.add_node("decomposition", self._decomposition_node)
        graph.add_node("tool_selection", self._tool_selection_node)
        graph.add_node("subquery_execution", self._subquery_execution_node)
        graph.add_node("synthesis", self._synthesis_node)
        graph.add_edge(START, "decomposition")
        graph.add_edge("decomposition", "tool_selection")
        graph.add_edge("tool_selection", "subquery_execution")
        graph.add_edge("subquery_execution", "synthesis")
        graph.add_edge("synthesis", END)
        return graph.compile()

    def _get_graph(self) -> Any:
        if self._compiled_graph is None:
            self._compiled_graph = self._build_graph()
        return self._compiled_graph

    @staticmethod
    def _append_timeline(
        timeline: list[RuntimeAgentGraphStep],
        step: str,
        status: str,
        details: Optional[dict[str, Any]] = None,
    ) -> list[RuntimeAgentGraphStep]:
        return timeline + [
            RuntimeAgentGraphStep(
                step=step,
                status=status,
                details=details or {},
            )
        ]

    @staticmethod
    def _emit_event(
        state: RuntimeOrchestrationState,
        event: str,
        data: dict[str, Any],
    ) -> None:
        callback = state.get("event_callback")
        if callback is None:
            return
        callback(event, data)

    def _decomposition_node(self, state: RuntimeOrchestrationState) -> RuntimeOrchestrationState:
        timeline = self._append_timeline(
            state["timeline"],
            "decomposition",
            "started",
            {"query": state["query"]},
        )
        self._emit_event(
            state,
            "heartbeat",
            {"step": "decomposition", "status": "started", "details": {"query": state["query"]}},
        )
        sub_queries = decompose_query(state["query"])
        timeline = self._append_timeline(
            timeline,
            "decomposition",
            "completed",
            {"sub_query_count": len(sub_queries)},
        )
        completed_payload = {
            "step": "decomposition",
            "status": "completed",
            "details": {"sub_query_count": len(sub_queries)},
        }
        self._emit_event(state, "heartbeat", completed_payload)
        self._emit_event(state, "sub_queries", {"sub_queries": sub_queries})
        return {
            "sub_queries": sub_queries,
            "timeline": timeline,
        }

    def _tool_selection_node(self, state: RuntimeOrchestrationState) -> RuntimeOrchestrationState:
        timeline = self._append_timeline(state["timeline"], "tool_selection", "started")
        self._emit_event(
            state,
            "heartbeat",
            {"step": "tool_selection", "status": "started", "details": {}},
        )
        tool_assignments = [
            SubQueryToolAssignment(sub_query=sub_query, tool=tool)
            for sub_query, tool in assign_tools_to_sub_queries(state["sub_queries"])
        ]
        assignments_payload = [assignment.model_dump() for assignment in tool_assignments]
        timeline = self._append_timeline(
            timeline,
            "tool_selection",
            "completed",
            {"assignments": assignments_payload},
        )
        self._emit_event(
            state,
            "heartbeat",
            {
                "step": "tool_selection",
                "status": "completed",
                "details": {"assignments": assignments_payload},
            },
        )
        self._emit_event(
            state,
            "tool_assignments",
            {"tool_assignments": assignments_payload},
        )
        return {
            "tool_assignments": tool_assignments,
            "timeline": timeline,
        }

    def _subquery_execution_node(
        self,
        state: RuntimeOrchestrationState,
    ) -> RuntimeOrchestrationState:
        timeline = state["timeline"]
        retrieval_results: list[SubQueryRetrievalResult] = []
        validation_results: list[SubQueryValidationResult] = []
        execution_results: list[SubQueryExecutionResult] = []

        for assignment in state["tool_assignments"]:
            retrieval_started_details = {
                "sub_query": assignment.sub_query,
                "tool": assignment.tool,
                "deep_agent": self.subquery_agent.name,
            }
            timeline = self._append_timeline(
                timeline,
                "subquery_execution.retrieval",
                "started",
                retrieval_started_details,
            )
            self._emit_event(
                state,
                "heartbeat",
                {
                    "step": "subquery_execution.retrieval",
                    "status": "started",
                    "details": retrieval_started_details,
                },
            )
            retrieval, validation = self.subquery_agent.run(assignment, state["db"])
            retrieval_results.append(retrieval)
            retrieval_payload = retrieval.model_dump()
            self._emit_event(state, "retrieval_result", retrieval_payload)
            timeline = self._append_timeline(
                timeline,
                "subquery_execution.retrieval",
                "completed",
                retrieval_started_details,
            )
            self._emit_event(
                state,
                "heartbeat",
                {
                    "step": "subquery_execution.retrieval",
                    "status": "completed",
                    "details": retrieval_started_details,
                },
            )
            validation_payload = validation.model_dump()
            timeline = self._append_timeline(
                timeline,
                "subquery_execution.validation",
                "completed",
                {
                    "sub_query": assignment.sub_query,
                    "tool": assignment.tool,
                    "status": validation.status,
                    "attempts": validation.attempts,
                    "follow_up_actions": validation.follow_up_actions,
                    "attempt_trace": [attempt.model_dump() for attempt in validation.attempt_trace],
                    "stop_reason": validation.stop_reason,
                    "deep_agent": self.subquery_agent.name,
                },
            )
            self._emit_event(
                state,
                "heartbeat",
                {
                    "step": "subquery_execution.validation",
                    "status": "completed",
                    "details": {
                        "sub_query": assignment.sub_query,
                        "tool": assignment.tool,
                        "status": validation.status,
                        "attempts": validation.attempts,
                        "follow_up_actions": validation.follow_up_actions,
                        "attempt_trace": [
                            attempt.model_dump() for attempt in validation.attempt_trace
                        ],
                        "stop_reason": validation.stop_reason,
                        "deep_agent": self.subquery_agent.name,
                    },
                },
            )
            self._emit_event(state, "validation_result", validation_payload)
            validation_results.append(validation)
            execution_result = SubQueryExecutionResult(
                sub_query=assignment.sub_query,
                tool=assignment.tool,
                retrieval_result=retrieval,
                validation_result=validation,
            )
            execution_results.append(
                execution_result
            )
            self._emit_event(
                state,
                "subquery_execution_result",
                execution_result.model_dump(),
            )

        return {
            "retrieval_results": retrieval_results,
            "validation_results": validation_results,
            "subquery_execution_results": execution_results,
            "timeline": timeline,
        }

    def _synthesis_node(self, state: RuntimeOrchestrationState) -> RuntimeOrchestrationState:
        timeline = self._append_timeline(state["timeline"], "synthesis", "started")
        self._emit_event(
            state,
            "heartbeat",
            {"step": "synthesis", "status": "started", "details": {}},
        )
        fallback_output = synthesize_answer(
            query=state["query"],
            execution_results=state["subquery_execution_results"],
        )
        evidence = self._build_validated_evidence(
            execution_results=state["subquery_execution_results"],
        )
        runtime_output = fallback_output
        runtime_mode = "disabled"
        if self.runtime_handle is not None and hasattr(self.runtime_handle, "synthesize"):
            runtime_output = self.runtime_handle.synthesize(
                query=state["query"],
                evidence=evidence,
                fallback_output=fallback_output,
            )
            runtime_mode = getattr(self.runtime_handle, "status", "unknown")
        timeline = self._append_timeline(timeline, "synthesis", "completed")
        self._emit_event(
            state,
            "heartbeat",
            {"step": "synthesis", "status": "completed", "details": {}},
        )
        return {
            "output": runtime_output,
            "runtime_mode": runtime_mode,
            "timeline": timeline,
        }

    @staticmethod
    def _build_validated_evidence(
        execution_results: list[SubQueryExecutionResult],
    ) -> str:
        lines: list[str] = []
        for execution_result in execution_results:
            retrieval = execution_result.retrieval_result
            validation = execution_result.validation_result
            if validation.status != "validated" or not validation.sufficient:
                continue

            if retrieval.tool == "internal":
                chunk_text = " ".join(chunk.content for chunk in retrieval.internal_results[:2]).strip()
                if chunk_text:
                    lines.append(f"{retrieval.sub_query}: {chunk_text}")
                continue

            page_text = " ".join(page.content for page in retrieval.opened_pages[:2]).strip()
            if page_text:
                lines.append(f"{retrieval.sub_query}: {page_text}")
                continue

            snippet_text = " ".join(item.snippet for item in retrieval.web_search_results[:2]).strip()
            if snippet_text:
                lines.append(f"{retrieval.sub_query}: {snippet_text}")

        return "\n".join(lines).strip()

    def build(self) -> dict[str, Any]:
        # Shape mirrors runtime topology and is exposed for observability/streaming.
        return {
            "kind": "langgraph-runtime",
            "name": self.name,
            "model": self.model,
            "compiled": True,
            "execution": "langgraph_invoke",
            "nodes": [
                "decomposition",
                "tool_selection",
                "subquery_execution.retrieval",
                "subquery_execution.validation",
                "synthesis",
            ],
            "edges": [
                ["decomposition", "tool_selection"],
                ["tool_selection", "subquery_execution.retrieval"],
                ["subquery_execution.retrieval", "subquery_execution.validation"],
                ["subquery_execution.validation", "synthesis"],
            ],
            "deep_agents": [
                {
                    "name": self.subquery_agent.name,
                    "nodes": ["retrieval", "validation"],
                    "kind": "langgraph-subgraph",
                }
            ],
        }

    def run(
        self,
        query: str,
        db: Session,
        event_callback: Optional[Callable[[str, dict[str, Any]], None]] = None,
    ) -> dict[str, Any]:
        final_state = self._get_graph().invoke(
            {
                "query": query,
                "db": db,
                "sub_queries": [],
                "tool_assignments": [],
                "retrieval_results": [],
                "validation_results": [],
                "subquery_execution_results": [],
                "output": "",
                "runtime_mode": "disabled",
                "timeline": [],
                "event_callback": event_callback,
            }
        )
        sub_queries = final_state["sub_queries"]
        tool_assignments = final_state["tool_assignments"]
        retrieval_results = final_state["retrieval_results"]
        validation_results = final_state["validation_results"]
        subquery_execution_results = final_state["subquery_execution_results"]
        runtime_output = final_state["output"]
        timeline = final_state["timeline"]
        runtime_mode = final_state["runtime_mode"]

        return {
            "sub_queries": sub_queries,
            "tool_assignments": tool_assignments,
            "retrieval_results": retrieval_results,
            "validation_results": validation_results,
            "subquery_execution_results": subquery_execution_results,
            "output": runtime_output,
            "graph_state": RuntimeAgentGraphState(
                current_step="completed",
                timeline=timeline,
                graph={**self.build(), "runtime_mode": runtime_mode},
            ),
        }
