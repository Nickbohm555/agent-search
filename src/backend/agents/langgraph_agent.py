from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Any, TypedDict
from uuid import uuid4

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


class PipelineState(TypedDict):
    """State carried across the DeepAgent pipeline steps.

    Used in `LangGraphAgentScaffold.run()` for decomposition, tool selection,
    iterative subquery execution, and synthesis. Orchestration is DeepAgent-only
    (no LangGraph/StateGraph).
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

    Called from: `LangGraphAgentScaffold._execute_single_subquery_step`.
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
    """Runtime agent that orchestrates the retrieval pipeline via DeepAgent only.

    Called from: `AgentFactory.create_langgraph_agent()` and then
    `services.agent_service.run_runtime_agent()`. Uses DeepAgent library for
    orchestration; no LangGraph/StateGraph.
    """

    name: str
    model: str
    subquery_agent: SubQueryExecutionAgent = field(default_factory=SubQueryExecutionAgent)

    def _append_timeline_step(
        self,
        timeline: list[RuntimeAgentGraphStep],
        *,
        step: str,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> list[RuntimeAgentGraphStep]:
        """Return a new timeline list including one graph step record.

        Called from all pipeline step handlers in this class.
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

    def _runtime_metadata(self) -> dict[str, Any]:
        """Build runtime metadata for API responses. DeepAgent-only; no LangGraph."""

        runtime: dict[str, Any] = {
            "library": "deepagent",
            "model_provider": os.getenv("AGENT_MODEL_PROVIDER", "openai"),
            "model_name": os.getenv("AGENT_MODEL_NAME", self.model),
        }
        try:
            from deepagents import create_deep_agent  # type: ignore

            runtime["deep_agents_available"] = True
            runtime["deep_agents_factory"] = getattr(
                create_deep_agent, "__name__", "create_deep_agent"
            )
        except Exception:
            runtime["deep_agents_available"] = False
        return runtime

    def _decomposition_step(self, state: PipelineState) -> PipelineState:
        """Pipeline step: decompose user query into ordered sub-queries."""

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

    def _tool_selection_step(self, state: PipelineState) -> PipelineState:
        """Pipeline step: assign one tool path to each sub-query."""

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

    def _execute_single_subquery_step(self, state: PipelineState) -> PipelineState:
        """Pipeline step: run retrieval + validation for one pending sub-query."""

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

    def _synthesis_step(self, state: PipelineState) -> PipelineState:
        """Pipeline step: produce final response text from validated evidence."""

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

    def build(self, *, execution: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build serializable pipeline metadata for API responses. DeepAgent-only."""

        return {
            "kind": "deepagent-runtime",
            "name": self.name,
            "model": self.model,
            "runtime": self._runtime_metadata(),
            "nodes": [
                "decomposition",
                "tool_selection",
                "subquery_execution",
                "synthesis",
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
        """Execute the DeepAgent pipeline and return final response artifacts.

        Called from `services.agent_service.run_runtime_agent()`. Runs decomposition
        → tool selection → per-subquery execution (via subquery_agent) → synthesis.
        """
        execution_id = str(uuid4())
        state: PipelineState = {
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
        state = self._decomposition_step(state)
        state = self._tool_selection_step(state)
        while state["current_index"] < len(state["tool_assignments"]):
            state = self._execute_single_subquery_step(state)
        state = self._synthesis_step(state)

        timeline = state["timeline"]
        execution_steps = [
            step.step for step in timeline if step.status == "completed"
        ]

        return {
            "sub_queries": state["sub_queries"],
            "tool_assignments": state["tool_assignments"],
            "retrieval_results": state["retrieval_results"],
            "validation_results": state["validation_results"],
            "output": state["output"],
            "graph_state": RuntimeAgentGraphState(
                current_step=state["current_step"],
                timeline=timeline,
                graph=self.build(
                    execution={
                        "execution_id": execution_id,
                        "completed_steps": execution_steps,
                        "subquery_execution_count": len(state["retrieval_results"]),
                    },
                ),
            ),
        }
