from dataclasses import dataclass


@dataclass
class RuntimeAgent:
    name: str
    version: str = "0.1.0"

    def run(self, query: str) -> str:
        return f"[{self.name}] scaffold response for: {query}"
