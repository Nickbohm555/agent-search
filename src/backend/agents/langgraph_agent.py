from __future__ import annotations

import asyncio
import os
from typing import Any

from schemas import RuntimeAgentGraphState, RuntimeAgentGraphStep
from sqlalchemy.orm import Session


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
        """Initialize DeepAgent once; return cached agent."""
        if self._agent is not None:
            return self._agent
        from deepagents import create_deep_agent  # type: ignore

        config = get_config()
        backend = get_backend()
        subagents = get_subagents()
        self._agent = create_deep_agent(
            tools=get_tools(),
            system_prompt=get_system_prompt(),
            backend=backend,
            subagents=subagents,
            config=config,
        )
        return self._agent

    async def _astream_run(self, query: str):
        """Run agent.astream with stream_mode='updates'; yield chunks."""
        agent = self._get_or_create_agent()
        input_state = {"messages": [{"role": "user", "content": query}]}
        async for chunk in agent.astream(
            input_state,
            stream_mode="updates",
        ):
            yield chunk

    def run(self, query: str, db: Session) -> dict[str, Any]:
        """Entrypoint from FastAPI: initialize DeepAgent, astream with stream_mode='updates', return minimal response."""
        agent = self._get_or_create_agent()
        chunks = []

        async def collect():
            async for chunk in self._astream_run(query):
                chunks.append(chunk)

        asyncio.run(collect())

        # Minimal response shape for existing API contract; implement details later
        timeline = [
            RuntimeAgentGraphStep(step="stream", status="completed", details={"chunk_count": len(chunks)})
        ]
        return {
            "sub_queries": [],
            "tool_assignments": [],
            "retrieval_results": [],
            "validation_results": [],
            "output": "",
            "graph_state": RuntimeAgentGraphState(
                current_step="completed",
                timeline=timeline,
                graph={
                    "kind": "deepagent-runtime",
                    "name": self.name,
                    "model": self.model,
                },
            ),
        }
