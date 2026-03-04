from dataclasses import dataclass
from typing import Any


@dataclass
class LangGraphAgentScaffold:
    """Scaffold representation of a runtime LangGraph agent."""

    name: str
    model: str

    def build(self) -> dict[str, Any]:
        # Placeholder for LangGraph graph compilation.
        return {
            "kind": "langgraph-runtime-scaffold",
            "name": self.name,
            "model": self.model,
            "compiled": False,
        }
