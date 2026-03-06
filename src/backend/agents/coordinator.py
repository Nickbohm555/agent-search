from __future__ import annotations

import logging
from typing import Any, Callable

from deepagents.backends import StateBackend

from tools import make_retriever_tool

logger = logging.getLogger(__name__)

_FLOW_TRACKING_FILE = "/runtime/coordinator_flow.md"
_COORDINATOR_PROMPT = (
    "You are the coordinator agent.\n"
    "Your job is to break the user query into ATOMIC subquestions and delegate each to the RAG subagent.\n\n"
    "You MUST track pipeline progress with deep-agents planning and virtual filesystem tools:\n"
    "- Call write_todos at the beginning to seed all pipeline stages.\n"
    f"- Use read_file and write_file on {_FLOW_TRACKING_FILE} to persist and update flow state.\n"
    "- Keep write_todos and the flow file in sync: mark in_progress and completed as work advances.\n"
    "- Do not use custom file I/O. Use only deep-agents virtual filesystem tools.\n\n"
    "Flow stages to mirror in write_todos and flow file:\n"
    "1. Initial exploratory/full search on original question plus decomposition setup.\n"
    "2. Decompose question into initial sub-questions.\n"
    "3. For each initial sub-question (parallel): Expand -> Search -> Validate -> Rerank -> Answer -> Check.\n"
    "4. Generate initial answer from initial search + sub-answers.\n"
    "5. Decide whether refinement is needed.\n"
    "6. If refinement is needed, generate informed refined sub-questions from gaps/unanswered parts.\n"
    "7. For each refined sub-question (parallel): Expand -> Search -> Validate -> Rerank -> Answer -> Check.\n"
    "8. Produce and validate refined answer.\n"
    "9. Compare refined answer to initial answer and output final answer.\n\n"
    "Sub-question rules:\n"
    "- Break each question into as many subquestions as possible.\n"
    "- One topic or entity per sub-question.\n"
    "- Ask the question directly and always end with '?'.\n\n"
    "After you have subanswers, use them to answer the main question with one concise answer."
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
    backend_factory: Callable[..., Any] | None = None,
) -> Any:
    """Create a coordinator agent with one RAG subagent backed by the retriever tool."""
    create_deep_agent_impl = create_deep_agent_fn or _default_create_deep_agent()
    backend = backend_factory or StateBackend
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
        "Building coordinator agent model=%r main_tools=%s subagents=%s backend=%s flow_file=%s",
        model,
        main_agent_tools,
        [rag_subagent["name"]],
        getattr(backend, "__name__", str(backend)),
        _FLOW_TRACKING_FILE,
    )
    runnable = create_deep_agent_impl(
        model=model,
        tools=main_agent_tools,
        system_prompt=_COORDINATOR_PROMPT,
        subagents=[rag_subagent],
        backend=backend,
    )

    logger.info(
        "Coordinator agent ready main_agent=coordinator subagent=%s tool=%s backend=%s",
        rag_subagent["name"],
        retriever_tool.name,
        getattr(backend, "__name__", str(backend)),
    )
    logger.info(
        "Coordinator subagent guardrail enabled subagent=%s final_message_only=true",
        rag_subagent["name"],
    )
    return _LoggingRunnable(runnable)
