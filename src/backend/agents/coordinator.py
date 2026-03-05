from __future__ import annotations

import logging
from typing import Any, Callable

from tools import make_retriever_tool

logger = logging.getLogger(__name__)

_COORDINATOR_PROMPT = (
    "You are the coordinator agent. Your job is to break the user query into ATOMIC subquestions and delegate each to the RAG subagent.\n\n"
    "Sub-question rules (from agent-search best practice):\n"
    "- break each question into as many subquestions as possible.\n"
    "- One topic or entity per sub-question: never put more than one proper noun or concept in a single question.\n"
    "- Ask the question directly; do not say 'research ...' or 'answer this question...'. Always end with '?'.\n\n"
    " Always end with '?'"
    "After you have subanswers, use them to answer the main question. Respond with one concise answer."
)
_RAG_SUBAGENT_NAME = "rag_retriever"
_RAG_SUBAGENT_PROMPT = (
    "You are the retrieval subagent. Read the incoming question. it should be atomic. If it is not, break it down further until it is."
    "Ask that exact subquestion to the retriever tool. If it gives you relevant docs, use them to answer the question and send that answer back to the coordinator agent. "
    "If it does not give you relevant docs, say 'nothing relevant found' and send that answer back to the coordinator agent. "
    "here is the format to send back to the coordinator agent: {subquestion}: {answer}"
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
        "description": "This agent is a RAG subagent which answers each sub-question using the retriever tool.",
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
        "Coordinator subagent guardrail enabled subagent=%s final_message_only=true",
        rag_subagent["name"],
    )
    return _LoggingRunnable(runnable)
