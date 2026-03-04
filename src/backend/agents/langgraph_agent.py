from dataclasses import dataclass, field
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
    runtime_handle: Any | None = None
    subquery_agent: SubQueryExecutionAgent = field(default_factory=SubQueryExecutionAgent)

    @staticmethod
    def _build_validated_evidence(
        retrieval_results: list[SubQueryRetrievalResult],
        validation_results: list[SubQueryValidationResult],
    ) -> str:
        validation_by_sub_query = {result.sub_query: result for result in validation_results}
        lines: list[str] = []
        for retrieval in retrieval_results:
            validation = validation_by_sub_query.get(retrieval.sub_query)
            if validation is None or validation.status != "validated" or not validation.sufficient:
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
        # Shape mirrors a compiled LangGraph topology projection for observability/streaming.
        return {
            "kind": "langgraph-runtime",
            "name": self.name,
            "model": self.model,
            "compiled": True,
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
        fallback_output = synthesize_answer(
            query=query,
            retrieval_results=retrieval_results,
            validation_results=validation_results,
        )
        evidence = self._build_validated_evidence(
            retrieval_results=retrieval_results,
            validation_results=validation_results,
        )
        runtime_output = fallback_output
        runtime_mode = "disabled"
        if self.runtime_handle is not None and hasattr(self.runtime_handle, "synthesize"):
            runtime_output = self.runtime_handle.synthesize(
                query=query,
                evidence=evidence,
                fallback_output=fallback_output,
            )
            runtime_mode = getattr(self.runtime_handle, "status", "unknown")
        timeline.append(RuntimeAgentGraphStep(step="synthesis", status="completed"))

        return {
            "sub_queries": sub_queries,
            "tool_assignments": tool_assignments,
            "retrieval_results": retrieval_results,
            "validation_results": validation_results,
            "output": runtime_output,
            "graph_state": RuntimeAgentGraphState(
                current_step="completed",
                timeline=timeline,
                graph={**self.build(), "runtime_mode": runtime_mode},
            ),
        }
