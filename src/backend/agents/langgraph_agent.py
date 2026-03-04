from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from schemas import (
    RuntimeAgentGraphState,
    RuntimeAgentGraphStep,
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


class LangGraphExecutionState(TypedDict):
    """State carried across the compiled LangGraph runtime nodes.

    Called from: `LangGraphAgentScaffold.run()` via `CompiledStateGraph.invoke(...)`.
    Why it exists: keeps one typed state contract across decomposition, tool selection,
    iterative subquery execution, and synthesis.
    Inputs: seeded in `run(...)` with query, db session, and empty collections.
    Outputs: finalized in synthesis node with answer text and execution timeline.
    Side effects: node functions append observability entries to `timeline`.
    """

    query: str
    db: Session
    execution_id: str
    sub_queries: list[str]
    tool_assignments: list[SubQueryToolAssignment]
    retrieval_results: list[SubQueryRetrievalResult]
    validation_results: list[SubQueryValidationResult]
    current_index: int
    output: str
    current_step: str
    timeline: list[RuntimeAgentGraphStep]


@dataclass
class SubQueryExecutionAgent:
    """Deep agent that owns retrieval + validation for one sub-query.

    Called from: `LangGraphAgentScaffold._execute_single_subquery_node`.
    Why it exists: centralizes retrieval + validation sequencing for each sub-query.
    Inputs: one tool assignment and a live SQLAlchemy session.
    Outputs: validated retrieval payload + validation outcome.
    Side effects: performs DB/web retrieval through service layer.
    """

    name: str = "subquery_execution_agent"

    def run(
        self,
        assignment: SubQueryToolAssignment,
        db: Session,
    ) -> tuple[SubQueryRetrievalResult, SubQueryValidationResult]:
        retrieval = execute_subquery_retrieval(assignment, db)
        return validate_retrieval_result(retrieval, db)


@dataclass
class LangGraphAgentScaffold:
    """Runtime graph agent that orchestrates the retrieval pipeline via LangGraph.

    Called from: `AgentFactory.create_langgraph_agent()` and then
    `services.agent_service.run_runtime_agent()`.
    Why it exists: builds one compiled LangGraph runtime that executes deterministic
    orchestration steps for each `/api/agents/run` request.
    """

    name: str
    model: str
    subquery_agent: SubQueryExecutionAgent = field(default_factory=SubQueryExecutionAgent)
    _compiled_graph: Any = field(default=None, init=False, repr=False)

    def _append_timeline_step(
        self,
        timeline: list[RuntimeAgentGraphStep],
        *,
        step: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> list[RuntimeAgentGraphStep]:
        """Return a new timeline list including one graph step record.

        Called from all node handlers in this class.
        Why it exists: keep timeline updates immutable and consistent across nodes.
        Inputs: current timeline, step name, status, optional details payload.
        Outputs: copied timeline with one appended `RuntimeAgentGraphStep`.
        Side effects: none.
        """

        updated = list(timeline)
        updated.append(
            RuntimeAgentGraphStep(step=step, status=status, details=details or {})
        )
        return updated

    def _initialize_langgraph_runtime(self, compiled_graph: Any | None) -> dict[str, Any]:
        """Build runtime metadata from actual graph compilation state.

        Called from `build(...)`.
        Why it exists: expose concrete LangGraph runtime characteristics to API
        consumers without leaking graph object internals.
        Inputs: currently compiled graph object (if available).
        Outputs: serializable runtime metadata dict.
        Side effects: optional import probe for Deep Agents package.
        """

        runtime: dict[str, Any] = {
            "library": "langgraph",
            "initialized": compiled_graph is not None,
            "deep_agents_imported": False,
            "compiled_graph_available": compiled_graph is not None,
            "compiled_graph_type": type(compiled_graph).__name__
            if compiled_graph is not None
            else None,
            "model_provider": os.getenv("AGENT_MODEL_PROVIDER", "openai"),
            "model_name": os.getenv("AGENT_MODEL_NAME", self.model),
        }

        try:
            from deepagents import create_deep_agent  # type: ignore

            runtime["deep_agents_imported"] = True
            runtime["deep_agents_factory"] = getattr(
                create_deep_agent, "__name__", "create_deep_agent"
            )
        except Exception:
            runtime["deep_agents_imported"] = False

        return runtime

    def _decomposition_node(self, state: LangGraphExecutionState) -> LangGraphExecutionState:
        """LangGraph node: decompose user query into ordered sub-queries."""

        timeline = self._append_timeline_step(
            state["timeline"],
            step="decomposition",
            status="started",
            details={"query": state["query"]},
        )
        sub_queries = decompose_query(state["query"])
        timeline = self._append_timeline_step(
            timeline,
            step="decomposition",
            status="completed",
            details={"sub_query_count": len(sub_queries)},
        )
        return {
            **state,
            "sub_queries": sub_queries,
            "current_step": "decomposition.completed",
            "timeline": timeline,
        }

    def _tool_selection_node(self, state: LangGraphExecutionState) -> LangGraphExecutionState:
        """LangGraph node: assign one tool path to each sub-query."""

        timeline = self._append_timeline_step(
            state["timeline"],
            step="tool_selection",
            status="started",
        )
        assignments = [
            SubQueryToolAssignment(sub_query=sub_query, tool=tool)
            for sub_query, tool in assign_tools_to_sub_queries(state["sub_queries"])
        ]
        timeline = self._append_timeline_step(
            timeline,
            step="tool_selection",
            status="completed",
            details={"assignments": [assignment.model_dump() for assignment in assignments]},
        )
        return {
            **state,
            "tool_assignments": assignments,
            "current_step": "tool_selection.completed",
            "timeline": timeline,
        }

    def _execute_single_subquery_node(
        self, state: LangGraphExecutionState
    ) -> LangGraphExecutionState:
        """LangGraph node: run retrieval + validation for one pending sub-query.

        Called by LangGraph in a loop through a conditional edge.
        Why it exists: each invocation advances exactly one sub-query execution so
        timeline/state mirrors real node progression.
        Inputs: state with `tool_assignments` and `current_index`.
        Outputs: state updated with one retrieval result + validation result.
        Side effects: calls retrieval services and validation services.
        """

        idx = state["current_index"]
        if idx >= len(state["tool_assignments"]):
            return state

        assignment = state["tool_assignments"][idx]
        timeline = self._append_timeline_step(
            state["timeline"],
            step="subquery_execution.retrieval",
            status="started",
            details={"sub_query": assignment.sub_query, "tool": assignment.tool},
        )
        retrieval, validation = self.subquery_agent.run(assignment, state["db"])
        timeline = self._append_timeline_step(
            timeline,
            step="subquery_execution.retrieval",
            status="completed",
            details={"sub_query": assignment.sub_query, "tool": assignment.tool},
        )
        timeline = self._append_timeline_step(
            timeline,
            step="subquery_execution.validation",
            status="completed",
            details={
                "sub_query": assignment.sub_query,
                "tool": assignment.tool,
                "status": validation.status,
                "attempts": validation.attempts,
                "follow_up_actions": validation.follow_up_actions,
            },
        )
        return {
            **state,
            "retrieval_results": [*state["retrieval_results"], retrieval],
            "validation_results": [*state["validation_results"], validation],
            "current_index": idx + 1,
            "current_step": "subquery_execution.validation.completed",
            "timeline": timeline,
        }

    def _route_after_subquery_execution(self, state: LangGraphExecutionState) -> str:
        """LangGraph conditional router for per-subquery execution loop."""

        if state["current_index"] < len(state["tool_assignments"]):
            return "subquery_execution"
        return "synthesis"

    def _synthesis_node(self, state: LangGraphExecutionState) -> LangGraphExecutionState:
        """LangGraph node: produce final response text from validated evidence."""

        timeline = self._append_timeline_step(
            state["timeline"],
            step="synthesis",
            status="started",
        )
        output = synthesize_answer(
            query=state["query"],
            retrieval_results=state["retrieval_results"],
            validation_results=state["validation_results"],
        )
        timeline = self._append_timeline_step(
            timeline,
            step="synthesis",
            status="completed",
        )
        return {
            **state,
            "output": output,
            "current_step": "completed",
            "timeline": timeline,
        }

    def _build_compiled_graph(self) -> Any:
        """Compile and return the LangGraph runtime for this agent instance.

        Called from: `_get_compiled_graph()`.
        Why it exists: defines node/edge topology once and compiles a reusable graph.
        Outputs: compiled LangGraph object with `.invoke(...)` support.
        Side effects: none.
        """

        graph = StateGraph(LangGraphExecutionState)
        graph.add_node("decomposition", self._decomposition_node)
        graph.add_node("tool_selection", self._tool_selection_node)
        graph.add_node("subquery_execution", self._execute_single_subquery_node)
        graph.add_node("synthesis", self._synthesis_node)

        graph.add_edge(START, "decomposition")
        graph.add_edge("decomposition", "tool_selection")
        graph.add_edge("tool_selection", "subquery_execution")
        graph.add_conditional_edges(
            "subquery_execution",
            self._route_after_subquery_execution,
            {
                "subquery_execution": "subquery_execution",
                "synthesis": "synthesis",
            },
        )
        graph.add_edge("synthesis", END)
        return graph.compile()

    def _get_compiled_graph(self) -> Any:
        """Return a cached compiled graph, compiling lazily on first use."""

        if self._compiled_graph is None:
            self._compiled_graph = self._build_compiled_graph()
        return self._compiled_graph

    def build(self, compiled_graph: Any | None = None, *, execution: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build serializable graph metadata for API responses.

        Called from `run(...)` when projecting `graph_state`.
        Why it exists: retain topology/runtime visibility while returning plain JSON.
        Inputs: compiled graph and optional execution summary.
        Outputs: graph metadata for consumers (UI, streaming, MCP).
        Side effects: none.
        """

        active_compiled_graph = compiled_graph or self._compiled_graph
        return {
            "kind": "langgraph-runtime",
            "name": self.name,
            "model": self.model,
            "compiled": active_compiled_graph is not None,
            "runtime": self._initialize_langgraph_runtime(active_compiled_graph),
            "nodes": [
                "decomposition",
                "tool_selection",
                "subquery_execution",
                "synthesis",
            ],
            "edges": [
                ["decomposition", "tool_selection"],
                ["tool_selection", "subquery_execution"],
                ["subquery_execution", "subquery_execution"],
                ["subquery_execution", "synthesis"],
            ],
            "deep_agents": [
                {
                    "name": self.subquery_agent.name,
                    "nodes": ["retrieval", "validation"],
                }
            ],
            "execution": execution or {},
        }

    def run(self, query: str, db: Session) -> dict[str, Any]:
        """Execute the compiled LangGraph and project final response artifacts.

        Called from `services.agent_service.run_runtime_agent()`.
        Why it exists: this is the single runtime entrypoint for `/api/agents/run`.
        Inputs: user query text and SQLAlchemy session.
        Outputs: normalized pipeline payload consumed by schema response builder.
        Side effects: retrieval/validation may access DB and web services.
        """

        compiled_graph = self._get_compiled_graph()
        execution_id = str(uuid4())
        initial_state: LangGraphExecutionState = {
            "query": query,
            "db": db,
            "execution_id": execution_id,
            "sub_queries": [],
            "tool_assignments": [],
            "retrieval_results": [],
            "validation_results": [],
            "current_index": 0,
            "output": "",
            "current_step": "initialized",
            "timeline": [],
        }
        final_state = compiled_graph.invoke(initial_state)
        timeline = final_state["timeline"]
        execution_steps = [
            step.step for step in timeline if step.status == "completed"
        ]

        return {
            "sub_queries": final_state["sub_queries"],
            "tool_assignments": final_state["tool_assignments"],
            "retrieval_results": final_state["retrieval_results"],
            "validation_results": final_state["validation_results"],
            "output": final_state["output"],
            "graph_state": RuntimeAgentGraphState(
                current_step=final_state["current_step"],
                timeline=timeline,
                graph=self.build(
                    compiled_graph,
                    execution={
                        "execution_id": execution_id,
                        "invoke_method": "compiled_graph.invoke",
                        "completed_steps": execution_steps,
                        "subquery_execution_count": len(final_state["retrieval_results"]),
                    },
                ),
            ),
        }
