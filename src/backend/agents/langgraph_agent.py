from dataclasses import dataclass, field
import os
from typing import Any

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


@dataclass
class SubQueryExecutionAgent:
    """Deep agent that owns retrieval + validation for one sub-query."""

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
    """Runtime graph agent that orchestrates the full retrieval pipeline."""

    name: str
    model: str
    subquery_agent: SubQueryExecutionAgent = field(default_factory=SubQueryExecutionAgent)

    def _initialize_langgraph_runtime(self) -> dict[str, Any]:
        """Scaffold-only runtime metadata with optional Deep Agents import."""
        runtime: dict[str, Any] = {
            "library": "langgraph",
            "initialized": False,
            "deep_agents_imported": False,
            "compiled_graph_available": False,
            "model_provider": os.getenv("AGENT_MODEL_PROVIDER", "openai"),
            "model_name": os.getenv("AGENT_MODEL_NAME", self.model),
        }

        try:
            from deepagents import create_deep_agent  # type: ignore

            runtime["deep_agents_imported"] = True
            runtime["deep_agents_factory"] = getattr(create_deep_agent, "__name__", "create_deep_agent")
            runtime["initialized"] = True
        except Exception:
            runtime["deep_agents_imported"] = False
            runtime["compiled_graph_available"] = False

        return runtime

    def build(self) -> dict[str, Any]:
        # Shape mirrors a compiled LangGraph topology projection for observability/streaming.
        return {
            "kind": "langgraph-runtime",
            "name": self.name,
            "model": self.model,
            "compiled": True,
            "runtime": self._initialize_langgraph_runtime(),
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
                }
            ],
        }

    def run(self, query: str, db: Session) -> dict[str, Any]:
        timeline: list[RuntimeAgentGraphStep] = []
        timeline.append(
            RuntimeAgentGraphStep(step="decomposition", status="started", details={"query": query})
        )
        sub_queries = decompose_query(query)
        timeline.append(
            RuntimeAgentGraphStep(
                step="decomposition",
                status="completed",
                details={"sub_query_count": len(sub_queries)},
            )
        )

        timeline.append(RuntimeAgentGraphStep(step="tool_selection", status="started"))
        tool_assignments = [
            SubQueryToolAssignment(sub_query=sub_query, tool=tool)
            for sub_query, tool in assign_tools_to_sub_queries(sub_queries)
        ]
        timeline.append(
            RuntimeAgentGraphStep(
                step="tool_selection",
                status="completed",
                details={"assignments": [assignment.model_dump() for assignment in tool_assignments]},
            )
        )

        retrieval_results: list[SubQueryRetrievalResult] = []
        validation_results: list[SubQueryValidationResult] = []

        for assignment in tool_assignments:
            timeline.append(
                RuntimeAgentGraphStep(
                    step="subquery_execution.retrieval",
                    status="started",
                    details={"sub_query": assignment.sub_query, "tool": assignment.tool},
                )
            )
            retrieval, validation = self.subquery_agent.run(assignment, db)
            retrieval_results.append(retrieval)
            timeline.append(
                RuntimeAgentGraphStep(
                    step="subquery_execution.retrieval",
                    status="completed",
                    details={"sub_query": assignment.sub_query, "tool": assignment.tool},
                )
            )
            timeline.append(
                RuntimeAgentGraphStep(
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
            )
            validation_results.append(validation)

        timeline.append(RuntimeAgentGraphStep(step="synthesis", status="started"))
        output = synthesize_answer(
            query=query,
            retrieval_results=retrieval_results,
            validation_results=validation_results,
        )
        timeline.append(RuntimeAgentGraphStep(step="synthesis", status="completed"))

        return {
            "sub_queries": sub_queries,
            "tool_assignments": tool_assignments,
            "retrieval_results": retrieval_results,
            "validation_results": validation_results,
            "output": output,
            "graph_state": RuntimeAgentGraphState(
                current_step="completed",
                timeline=timeline,
                graph=self.build(),
            ),
        }
