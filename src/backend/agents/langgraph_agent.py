from __future__ import annotations

import os
from hashlib import sha256
import json
from dataclasses import dataclass
from threading import Lock
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


@dataclass(frozen=True)
class RuntimeContext:
    """Runtime invocation context used by persistence wiring."""

    user_id: str


class DeepAgentPersistenceStore:
    """In-process persistence for DeepAgent-like checkpoint and store semantics.

    Called by `LangGraphAgentScaffold.run` to emulate thread checkpointing and a
    user-scoped cross-thread store while the project remains scaffold-only.
    """

    def __init__(self) -> None:
        self._thread_checkpoints: dict[str, list[dict[str, Any]]] = {}
        self._store: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
        self._lock = Lock()

    def _memory_namespace(self, context: RuntimeContext) -> tuple[str, str]:
        """Resolve a deterministic memory namespace from runtime context."""
        return (context.user_id, "memories")

    def get_thread_state(
        self, thread_id: str, checkpoint_id: str | None = None
    ) -> dict[str, Any]:
        """Return persisted thread state before executing the current run.

        Inputs:
        - `thread_id`: thread namespace for checkpoints.
        - `checkpoint_id`: optional checkpoint replay target.
        Output:
        - summary used by graph execution metadata and tests.
        """
        with self._lock:
            history = list(self._thread_checkpoints.get(thread_id, []))

        selected_checkpoint = None
        if checkpoint_id:
            selected_checkpoint = next(
                (item for item in history if item["checkpoint_id"] == checkpoint_id),
                None,
            )

        return {
            "checkpoint_count": len(history),
            "checkpoint_ids": [item["checkpoint_id"] for item in history],
            "replayed_checkpoint_id": checkpoint_id if selected_checkpoint else None,
            "known_checkpoint": selected_checkpoint is not None if checkpoint_id else None,
            "previous_output": selected_checkpoint["output"] if selected_checkpoint else None,
            "latest_output": history[-1]["output"] if history else None,
            "previous_query": selected_checkpoint["query"] if selected_checkpoint else None,
            "latest_query": history[-1]["query"] if history else None,
        }

    def get_store_state(self, context: RuntimeContext) -> dict[str, Any]:
        """Return user-scoped cross-thread namespace metadata before run execution."""
        namespace = self._memory_namespace(context)
        with self._lock:
            namespace_entries = list(self._store.get(namespace, {}).values())
        return {
            "namespace": list(namespace),
            "entry_count": len(namespace_entries),
            "thread_ids": sorted({entry["last_writer_thread_id"] for entry in namespace_entries}),
        }

    def read_memories(
        self,
        *,
        context: RuntimeContext,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Read deterministic memory values for a user namespace before synthesis.

        Called by `LangGraphAgentScaffold.run` during explicit memory-routing read.
        Inputs:
        - `context`: resolved runtime context containing `user_id`.
        - `query`: current run query; included for future semantic filtering.
        - `limit`: max memories to return.
        Output:
        - newest-first deterministic memory entries for metadata/timeline.
        """
        del query  # semantic query routing is optional in scaffold mode.
        namespace = self._memory_namespace(context)
        with self._lock:
            entries = list(self._store.get(namespace, {}).values())
        entries.sort(key=lambda item: item["memory_id"], reverse=True)
        return entries[:limit]

    def _build_memory_payload(self, *, query: str, output: str) -> dict[str, str]:
        """Build a deterministic memory value from run input/output."""
        return {
            "kind": "final_answer_summary",
            "query": query,
            "summary": output,
        }

    def write_memory(
        self,
        *,
        context: RuntimeContext,
        thread_id: str,
        query: str,
        output: str,
    ) -> dict[str, Any]:
        """Write a deterministic memory value after synthesis for a user namespace.

        Called by `LangGraphAgentScaffold.run` after synthesis completes to model
        explicit memory-routing write behavior.
        Inputs:
        - `context`: resolved runtime context containing `user_id`.
        - `thread_id`: thread that produced the memory.
        - `query`: query persisted in deterministic memory payload.
        - `output`: synthesized summary persisted in deterministic payload.
        Output:
        - stored memory record (`memory_id` + `value`) for metadata/timeline.
        Side effects:
        - upserts namespace memory entry keyed by deterministic `memory_id`.
        """
        namespace = self._memory_namespace(context)
        memory_value = self._build_memory_payload(query=query, output=output)
        memory_key_source = json.dumps(memory_value, sort_keys=True)
        memory_id = sha256(memory_key_source.encode("utf-8")).hexdigest()[:16]

        with self._lock:
            namespace_entries = self._store.setdefault(namespace, {})
            namespace_entries[memory_id] = {
                "memory_id": memory_id,
                "value": memory_value,
                "last_writer_thread_id": thread_id,
            }
            stored_entry = dict(namespace_entries[memory_id])
        return stored_entry

    def persist_thread_checkpoint(
        self,
        *,
        thread_id: str,
        query: str,
        output: str,
        checkpoint_id: str | None = None,
    ) -> str:
        """Persist one run checkpoint in thread history for replay/time-travel."""
        checkpoint_value = checkpoint_id or str(uuid4())
        checkpoint_data = {
            "checkpoint_id": checkpoint_value,
            "query": query,
            "output": output,
        }

        with self._lock:
            self._thread_checkpoints.setdefault(thread_id, []).append(checkpoint_data)
        return checkpoint_value


# --- Agent scaffold ---


class LangGraphAgentScaffold:
    """DeepAgent used by FastAPI /api/agents/run. Initialized with tools, system_prompt, backend, subagents, config."""

    _shared_persistence = DeepAgentPersistenceStore()

    def __init__(self, name: str = "agent", model: str = "gpt-4o-mini"):
        self.name = name
        self.model = model
        self._agent = None
        self._persistence = self._shared_persistence

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

        context = RuntimeContext(user_id=payload.user_id or "anonymous")

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
        context = deepagent_run_config["context"]
        persisted_thread_state = self._persistence.get_thread_state(
            thread_id=thread_id,
            checkpoint_id=payload.checkpoint_id,
        )
        persisted_store_state = self._persistence.get_store_state(context)
        execution_id = str(uuid4())
        memory_reads = self._persistence.read_memories(context=context, query=payload.query)

        timeline: list[RuntimeAgentGraphStep] = []
        timeline.append(RuntimeAgentGraphStep(step="memory.read", status="started"))
        timeline.append(
            RuntimeAgentGraphStep(
                step="memory.read",
                status="completed",
                details={"namespace": list((context.user_id, "memories")), "memory_count": len(memory_reads)},
            )
        )
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
        timeline.append(RuntimeAgentGraphStep(step="memory.write", status="started"))
        memory_write = self._persistence.write_memory(
            context=context,
            thread_id=thread_id,
            query=payload.query,
            output=output,
        )
        timeline.append(
            RuntimeAgentGraphStep(
                step="memory.write",
                status="completed",
                details={
                    "namespace": list((context.user_id, "memories")),
                    "memory_id": memory_write["memory_id"],
                },
            )
        )
        resolved_checkpoint_id = self._persistence.persist_thread_checkpoint(
            thread_id=thread_id,
            query=payload.query,
            output=output,
            checkpoint_id=payload.checkpoint_id,
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
                        "user_id": context.user_id,
                        "configurable": deepagent_run_config["configurable"],
                        "context": {"user_id": context.user_id},
                        "persistence": {
                            "thread_checkpoint_count_before_run": persisted_thread_state[
                                "checkpoint_count"
                            ],
                            "thread_checkpoint_ids_before_run": persisted_thread_state[
                                "checkpoint_ids"
                            ],
                            "replayed_checkpoint_id": persisted_thread_state[
                                "replayed_checkpoint_id"
                            ],
                            "known_checkpoint": persisted_thread_state["known_checkpoint"],
                            "resolved_checkpoint_id": resolved_checkpoint_id,
                            "store_namespace": persisted_store_state["namespace"],
                            "store_entry_count_before_run": persisted_store_state[
                                "entry_count"
                            ],
                            "store_thread_ids_before_run": persisted_store_state["thread_ids"],
                            "memory_reads_before_run": memory_reads,
                            "memory_write_after_synthesis": memory_write,
                        },
                    },
                    "deep_agents": [
                        {"name": "subquery_execution_agent", "nodes": ["retrieval", "validation"]}
                    ],
                },
            ),
        }
