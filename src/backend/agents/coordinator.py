from __future__ import annotations

import logging
from typing import Any, Callable

from tools import make_retriever_tool

logger = logging.getLogger(__name__)

_COORDINATOR_PROMPT = (
    "You are the coordinator agent for a multi-stage RAG pipeline. You must keep state with the write_todos planning tool.\n\n"
    "At the start of every run, call write_todos to create a plan that mirrors this flow, then keep it updated by marking items in_progress/completed:\n"
    "1) Initial question intake.\n"
    "2) In parallel: exploratory/full search on the original question and decomposition into initial sub-questions.\n"
    "3) For each initial sub-question, run: Expand -> Search -> Validate -> Rerank -> Answer -> Check.\n"
    "4) Generate the initial answer from initial-search context and all sub-answers.\n"
    "5) Decide if refinement is needed.\n"
    "6) If refinement is needed: generate informed refined sub-questions from gaps/unanswered parts.\n"
    "7) For each refined sub-question, run: Expand -> Search -> Validate -> Rerank -> Answer -> Check.\n"
    "8) Produce and validate refined answer.\n"
    "9) Compare refined vs initial answer and output final answer.\n\n"
    "Do not add an 'Entity Relationship' stage.\n\n"
    "Sub-question rules:\n"
    "- Break the user query into focused, atomic sub-questions.\n"
    "- One topic/entity per sub-question; no multi-entity compound questions.\n"
    "- Ask direct questions and always end each sub-question with '?'.\n\n"
    "Delegate each sub-question to the RAG subagent. After sub-answers are returned, synthesize a concise final answer."
)
_RAG_SUBAGENT_NAME = "rag_retriever"
_RAG_SUBAGENT_PROMPT = (
    "You are the retrieval subagent. For each assigned sub-question, use the search_database "
    "tool to run similarity search over internal data. Answer that sub-question concisely "
    "using only retrieved content, and clearly indicate when the retrieval does not contain "
    "enough evidence. When you have finished answering the sub-question, send that answer as "
    "your final message and do not make any further tool calls after providing the answer."
)


class _LoggingRunnable:
    def __init__(self, runnable: Any) -> None:
        self._runnable = runnable

    def invoke(self, input: Any, *args: Any, **kwargs: Any) -> Any:
        logger.info("Coordinator agent invoke start subagent=%s", _RAG_SUBAGENT_NAME)
        result = self._runnable.invoke(input, *args, **kwargs)
        logger.info("Coordinator agent invoke complete subagent=%s", _RAG_SUBAGENT_NAME)
        return result

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._runnable, attr)


def _default_create_deep_agent() -> Callable[..., Any]:
    try:
        from deepagents import create_deep_agent
    except Exception as exc:  # pragma: no cover - environment-specific dependency mismatch.
        logger.exception("Failed to import deepagents.create_deep_agent")
        raise RuntimeError("Deep agents dependency is unavailable. Check langgraph/deepagents install.") from exc
    return create_deep_agent


def create_coordinator_agent(
    vector_store: Any,
    model: Any,
    *,
    create_deep_agent_fn: Callable[..., Any] | None = None,
) -> Any:
    """Create a coordinator agent with one RAG subagent backed by the retriever tool."""
    create_deep_agent_impl = create_deep_agent_fn or _default_create_deep_agent()
    retriever_tool = make_retriever_tool(vector_store)
    # Subagent gets the retriever; main agent has no tools and delegates via task() only.
    rag_subagent = {
        "name": _RAG_SUBAGENT_NAME,
        "description": "Runs semantic retrieval against internal wiki chunks.",
        "system_prompt": _RAG_SUBAGENT_PROMPT,
        "tools": [retriever_tool],
    }

    main_agent_tools: list[Any] = []
    logger.info(
        "Building coordinator agent model=%r main_tools=%s subagents=%s",
        model,
        main_agent_tools,
        [rag_subagent["name"]],
    )
    runnable = create_deep_agent_impl(
        model=model,
        tools=main_agent_tools,
        system_prompt=_COORDINATOR_PROMPT,
        subagents=[rag_subagent],
    )

    logger.info(
        "Coordinator agent ready main_agent=coordinator subagent=%s tool=%s",
        rag_subagent["name"],
        retriever_tool.name,
    )
    logger.info(
        "Coordinator planning contract enabled tool=write_todos stages=initial_parallel,initial_pipeline,initial_answer,refinement_decision,refined_pipeline,compare_output",
    )
    logger.info(
        "Coordinator subagent guardrail enabled subagent=%s final_message_only=true",
        rag_subagent["name"],
    )
    return _LoggingRunnable(runnable)
