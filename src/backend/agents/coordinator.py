from __future__ import annotations

import logging
from typing import Any, Callable

from deepagents.backends import StateBackend

from tools import make_retriever_tool

logger = logging.getLogger(__name__)

_FLOW_TRACKING_FILE = "/runtime/coordinator_flow.md"
# Decomposition output contract:
# - Decomposition-only step must produce a list of sub-question strings.
# - Preferred format is JSON array of strings; newline-separated questions are accepted upstream.
# - Each question must be one concept and end with '?' after normalization.
_DECOMPOSITION_ONLY_PROMPT = (
    "You are a decomposition planner for retrieval.\n"
    "Task: break the user question into narrow, atomic sub-questions using the provided retrieval context.\n\n"
    "Rules:\n"
    "- Output only sub-questions; do not answer them.\n"
    "- One concept or entity per sub-question.\n"
    "- Every sub-question must end with '?'.\n"
    "- Prefer entities and concepts from the provided context.\n"
    "- Return valid JSON as an array of strings.\n"
)
_COORDINATOR_PROMPT = (
    "You are the coordinator agent.\n"
    "Your job is to delegate provided sub-questions to the RAG subagent and manage the pipeline state.\n\n"
    "You MUST track pipeline progress with deep-agents planning and virtual filesystem tools:\n"
    "- Call write_todos at the beginning to seed all pipeline stages.\n"
    f"- Use read_file and write_file on {_FLOW_TRACKING_FILE} to persist and update flow state.\n"
    f"- First call read_file on {_FLOW_TRACKING_FILE}; if missing, create it with write_file before any edit_file call.\n"
    f"- Create {_FLOW_TRACKING_FILE} once with write_file, then use read_file + edit_file for updates.\n"
    "- Do not call write_file on an existing file path.\n"
    "- Keep write_todos and the flow file in sync: mark in_progress and completed as work advances.\n"
    "- Do not use custom file I/O. Use only deep-agents virtual filesystem tools.\n\n"
    "Flow stages to mirror in write_todos and flow file:\n"
    "1. Initial exploratory/full search on original question plus decomposition setup.\n"
    "2. Consume provided initial sub-questions (already decomposed) and prepare delegation.\n"
    "3. For each initial sub-question (parallel): Expand -> Search -> Validate -> Rerank -> Answer -> Check.\n"
    "4. Confirm delegation complete and subagent responses are gathered for handoff.\n"
    "5. End with a short completion message; do not synthesize the final user answer.\n\n"
    "Delegation requirements for stage 2:\n"
    "- The user message will provide the exact initial sub-questions.\n"
    "- Do not decompose again in this same context window.\n"
    "- Delegate each provided sub-question via task(description=<exact sub-question>).\n"
    "- Preserve the provided order and trailing '?'.\n"
    "- Do not skip delegation, even if you can answer directly.\n\n"
    "Sub-question handling rules:\n"
    "- Treat each provided sub-question as atomic.\n"
    "- Do not merge, rewrite, or invent alternate initial sub-questions.\n"
    "- Only produce new sub-questions later if refinement is explicitly needed.\n\n"
    "Completion behavior:\n"
    "- The coordinator only delegates and gathers subagent outputs.\n"
    "- Do not synthesize or output the final answer to the main question.\n"
    "- End with a brief status message such as 'Delegation complete; subanswers collected.'"
)
_RAG_SUBAGENT_NAME = "rag_retriever"
_RAG_SUBAGENT_PROMPT = (
    "You are the retrieval subagent. Read the incoming question. it should be atomic. If it is not, break it down further until it is."
    "Generate one expanded query for that subquestion by adding close synonyms and compact reformulations."
    "Call the retriever tool with both fields: query=<exact subquestion> and expanded_query=<expanded query>."
    "If no useful expansion exists, set expanded_query equal to the original subquestion."
    "If the retriever gives relevant docs, use them to answer the question and send that answer back to the coordinator agent. "
    "If it does not give you relevant docs, say 'nothing relevant found' and send that answer back to the coordinator agent. "
    "here is the format to send back to the coordinator agent: {subquestion}: {answer}"
)


def get_decomposition_only_prompt() -> str:
    return _DECOMPOSITION_ONLY_PROMPT


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
