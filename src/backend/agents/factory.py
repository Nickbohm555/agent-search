from dataclasses import dataclass
from typing import Optional

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

    # this needs to be a DeepAgentLangGraph agent. with subagents, harness, prompts.
    # this will be our single source of truth for builiding the agents
    # add tools, prompts, subagents, harness, etc for our problem.
    def create_langgraph_agent(self) -> LangGraphAgentScaffold:
        """Return a runtime LangGraph agent instance."""
        return LangGraphAgentScaffold(
            name=self.config.agent_name,
            model=self.config.model_name,
        )

    def create_runtime_agent(self) -> RuntimeAgent:
        """Return app-level runtime agent wrapper."""
        return RuntimeAgent(name=self.config.agent_name)


def build_default_agent() -> RuntimeAgent:
    factory = AgentFactory()
    return factory.create_runtime_agent()
