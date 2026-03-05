from __future__ import annotations

import logging
from typing import Any, Callable

from tools import make_retriever_tool

logger = logging.getLogger(__name__)

_COORDINATOR_PROMPT = (
    "You are the coordinator agent. Break the user query into focused subquestions and "
    "delegate each one to the RAG subagent using the task tool. Do not answer with "
    "unsupported claims; synthesize only from delegated retrieval results."
)
_RAG_SUBAGENT_NAME = "rag_retriever"
_RAG_SUBAGENT_PROMPT = (
    "You are the retrieval subagent. Use the search_database tool to run similarity "
    "search over internal data and return concise, grounded findings from retrieved content."
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
    rag_subagent = {
        "name": _RAG_SUBAGENT_NAME,
        "description": "Runs semantic retrieval against internal wiki chunks.",
        "prompt": _RAG_SUBAGENT_PROMPT,
        "tools": [retriever_tool.name],
    }

    logger.info(
        "Building coordinator agent model=%r main_tools=%s subagents=%s",
        model,
        [],
        [rag_subagent["name"]],
    )
    try:
        runnable = create_deep_agent_impl(
            tools=[retriever_tool],
            instructions=_COORDINATOR_PROMPT,
            model=model,
            subagents=[rag_subagent],
            builtin_tools=[],
        )
    except TypeError:
        # Backward-compat path if builtin_tools is not supported.
        runnable = create_deep_agent_impl(
            tools=[retriever_tool],
            instructions=_COORDINATOR_PROMPT,
            model=model,
            subagents=[rag_subagent],
        )

    logger.info(
        "Coordinator agent ready main_agent=coordinator subagent=%s tool=%s",
        rag_subagent["name"],
        retriever_tool.name,
    )
    return _LoggingRunnable(runnable)
