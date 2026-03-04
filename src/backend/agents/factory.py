from dataclasses import dataclass
from typing import Any, Optional

from agents.base import RuntimeAgent
from agents.langgraph_agent import LangGraphAgentScaffold


@dataclass
class AgentFactoryConfig:
    """Scaffold config for runtime LangGraph agent construction."""

    agent_name: str = "agent-search-default"
    model_name: str = "gpt-5"


class AgentFactory:
    """Scaffold factory responsible for building runtime agents."""

    def __init__(self, config: Optional[AgentFactoryConfig] = None) -> None:
        self.config = config or AgentFactoryConfig()

    def create_langgraph_agent(self) -> Any:
        """Return a runtime LangGraph agent instance (scaffold placeholder)."""
        graph_agent = LangGraphAgentScaffold(
            name=self.config.agent_name,
            model=self.config.model_name,
        )
        return graph_agent.build()

    def create_runtime_agent(self) -> RuntimeAgent:
        """Return app-level runtime agent wrapper (scaffold)."""
        _graph = self.create_langgraph_agent()
        return RuntimeAgent(name=self.config.agent_name)


def build_default_agent() -> RuntimeAgent:
    factory = AgentFactory()
    return factory.create_runtime_agent()
