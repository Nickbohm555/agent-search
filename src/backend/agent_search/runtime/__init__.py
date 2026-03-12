from agent_search.runtime.state import RAGState

__all__ = ["RAGState", "run_runtime_agent"]


def __getattr__(name: str):
    if name == "run_runtime_agent":
        from agent_search.runtime.runner import run_runtime_agent

        return run_runtime_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
