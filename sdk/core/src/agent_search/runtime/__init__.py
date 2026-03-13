from agent_search.runtime.execution_identity import (
    ExecutionIdentityError,
    mint_thread_id,
    resolve_thread_identity,
    validate_thread_id,
)
from agent_search.runtime.resume import ResumeTransitionError
from agent_search.runtime.state import RAGState

__all__ = [
    "ExecutionIdentityError",
    "RAGState",
    "ResumeTransitionError",
    "mint_thread_id",
    "resolve_thread_identity",
    "run_runtime_agent",
    "validate_thread_id",
]


def __getattr__(name: str):
    if name == "run_runtime_agent":
        from agent_search.runtime.runner import run_runtime_agent

        return run_runtime_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
