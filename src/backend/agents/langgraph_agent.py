from __future__ import annotations

import os
from uuid import uuid4
from typing import Any

from schemas import (
    RuntimeAgentGraphState,
    RuntimeAgentGraphStep,
    RuntimeAgentRunRequest,
    SubQueryToolAssignment,
)
from sqlalchemy.orm import Session
from services.answer_synthesis_service import synthesize_answer
from services.retrieval_service import execute_subquery_retrievals
from services.validation_service import validate_retrieval_results
from utils.query_decomposition import decompose_query
from utils.tool_selection import assign_tools_to_sub_queries


# --- Scaffolding: implement details later ---


def get_tools():
    """Return tools for the deep agent (e.g. internet_search). Scaffold: empty list."""
    return []


def get_system_prompt() -> str:
    """Return system prompt for the deep agent. Scaffold: empty."""
    return ""


def get_backend():
    """Return backend for the deep agent. Scaffold: None."""
    return None


def get_subagents():
    """Return subagent definitions for the deep agent. Scaffold: empty list."""
    return []


def get_config() -> dict[str, Any]:
    """Return config for the deep agent (e.g. model, provider from env)."""
    return {
        "model": os.getenv("AGENT_MODEL_NAME", "gpt-4o-mini"),
        "provider": os.getenv("AGENT_MODEL_PROVIDER", "openai"),
    }


# --- Agent scaffold ---


class LangGraphAgentScaffold:
    """DeepAgent used by FastAPI /api/agents/run. Initialized with tools, system_prompt, backend, subagents, config."""

    def __init__(self, name: str = "agent", model: str = "gpt-4o-mini"):
        self.name = name
        self.model = model
        self._agent = None

    def _get_or_create_agent(self):
        """Initialize the DeepAgent runtime client once and return the cached instance."""
        if self._agent is not None:
            return self._agent
        from deepagents import create_deep_agent  # type: ignore

        config = get_config()
        model_name = config["model"]
        self._agent = create_deep_agent(
            tools=get_tools(),
            instructions=get_system_prompt(),
            subagents=get_subagents(),
            model=f"{config['provider']}:{model_name}",
        )
        return self._agent

    def _build_run_config(self, payload: RuntimeAgentRunRequest) -> tuple[str, dict[str, Any]]:
        """Build DeepAgent invocation config/context from API request fields.

        Called by `run` before retrieval execution so `thread_id`, optional
        `checkpoint_id`, and optional `user_id` are available in execution metadata
        and can be passed to the DeepAgent runtime during future persistence work.
        """
        thread_id = payload.thread_id or str(uuid4())
        configurable: dict[str, str] = {"thread_id": thread_id}
        if payload.checkpoint_id:
            configurable["checkpoint_id"] = payload.checkpoint_id

        context: dict[str, str] = {}
        if payload.user_id:
            context["user_id"] = payload.user_id

        return thread_id, {"configurable": configurable, "context": context}

    def run(self, payload: RuntimeAgentRunRequest, db: Session) -> dict[str, Any]:
        """Run the deterministic agent pipeline and return API response fields.

        Called by `services/agent_service.py::run_runtime_agent`.
        Inputs:
        - `payload`: user query plus optional persistence config.
        - `db`: SQLAlchemy session used by retrieval/validation services.
        Outputs:
        - dict consumed by `RuntimeAgentRunResponse` and graph metadata.
        Side effects:
        - reads internal-data tables and may call deterministic web-search fixtures.
        """
        thread_id, deepagent_run_config = self._build_run_config(payload)
        execution_id = str(uuid4())

        timeline: list[RuntimeAgentGraphStep] = []
        timeline.append(RuntimeAgentGraphStep(step="decomposition", status="started"))
        sub_queries = decompose_query(payload.query)
        timeline.append(
            RuntimeAgentGraphStep(
                step="decomposition",
                status="completed",
                details={"subquery_count": len(sub_queries)},
            )
        )

        timeline.append(RuntimeAgentGraphStep(step="tool_selection", status="started"))
        assignments = [
            SubQueryToolAssignment(sub_query=sub_query, tool=tool)
            for sub_query, tool in assign_tools_to_sub_queries(sub_queries)
        ]
        timeline.append(
            RuntimeAgentGraphStep(
                step="tool_selection",
                status="completed",
                details={"assignment_count": len(assignments)},
            )
        )

        retrieval_results = []
        validation_results = []
        for assignment in assignments:
            timeline.append(
                RuntimeAgentGraphStep(
                    step="subquery_execution.retrieval",
                    status="started",
                    details={"sub_query": assignment.sub_query, "tool": assignment.tool},
                )
            )
            retrieval_result = execute_subquery_retrievals([assignment], db)[0]
            retrieval_results.append(retrieval_result)
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
                    status="started",
                    details={"sub_query": assignment.sub_query, "tool": assignment.tool},
                )
            )
            validated_retrieval, validation = validate_retrieval_results([retrieval_result], db)
            retrieval_results[-1] = validated_retrieval[0]
            validation_results.append(validation[0])
            timeline.append(
                RuntimeAgentGraphStep(
                    step="subquery_execution.validation",
                    status="completed",
                    details={"sub_query": assignment.sub_query, "tool": assignment.tool},
                )
            )

        timeline.append(RuntimeAgentGraphStep(step="synthesis", status="started"))
        output = synthesize_answer(payload.query, retrieval_results, validation_results)
        timeline.append(
            RuntimeAgentGraphStep(
                step="synthesis",
                status="completed",
                details={"output_length": len(output)},
            )
        )

        return {
            "thread_id": thread_id,
            "checkpoint_id": payload.checkpoint_id,
            "sub_queries": sub_queries,
            "tool_assignments": assignments,
            "retrieval_results": retrieval_results,
            "validation_results": validation_results,
            "output": output,
            "graph_state": RuntimeAgentGraphState(
                current_step="completed",
                timeline=timeline,
                graph={
                    "kind": "deepagent-runtime",
                    "name": self.name,
                    "model": self.model,
                    "runtime": {"library": "deepagent"},
                    "execution": {
                        "execution_id": execution_id,
                        "subquery_execution_count": len(sub_queries),
                        "thread_id": thread_id,
                        "checkpoint_id": payload.checkpoint_id,
                        "user_id": payload.user_id,
                        "configurable": deepagent_run_config["configurable"],
                        "context": deepagent_run_config["context"],
                    },
                    "deep_agents": [
                        {"name": "subquery_execution_agent", "nodes": ["retrieval", "validation"]}
                    ],
                },
            ),
        }
