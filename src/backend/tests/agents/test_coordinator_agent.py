import logging
import sys
from pathlib import Path
from types import SimpleNamespace

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agents import create_coordinator_agent


class _FakeVectorStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def similarity_search(self, query: str, k: int, filter=None) -> list[Document]:
        self.calls.append({"query": query, "k": k, "filter": filter})
        return [
            Document(
                page_content="Hormuz shipping chokepoint summary.",
                metadata={"title": "Strait of Hormuz", "source": "https://en.wikipedia.org/wiki/Strait_of_Hormuz"},
            )
        ]


def test_create_coordinator_agent_returns_invocable_and_uses_rag_subagent(caplog) -> None:
    captured: dict[str, object] = {}

    class _FakeDeepAgent:
        def __init__(self, tool):
            self._tool = tool

        def invoke(self, payload):
            assert payload["messages"][0].content == "What is the Strait of Hormuz?"
            tool_output = self._tool.invoke({"query": "strait of hormuz", "limit": 1})
            return {"messages": [SimpleNamespace(content=f"Answer based on retrieval: {tool_output}")]}

    def fake_create_deep_agent(*, tools, instructions, model, subagents, builtin_tools=None):
        captured["tools"] = tools
        captured["instructions"] = instructions
        captured["model"] = model
        captured["subagents"] = subagents
        captured["builtin_tools"] = builtin_tools
        return _FakeDeepAgent(tools[0])

    store = _FakeVectorStore()
    with caplog.at_level(logging.INFO):
        agent = create_coordinator_agent(
            vector_store=store,
            model="fake-model",
            create_deep_agent_fn=fake_create_deep_agent,
        )
        result = agent.invoke({"messages": [HumanMessage(content="What is the Strait of Hormuz?")]})

    assert hasattr(agent, "invoke")
    assert captured["model"] == "fake-model"
    assert isinstance(captured["tools"], list)
    assert captured["tools"][0].name == "search_database"
    assert "Break the user query into focused subquestions" in str(captured["instructions"])
    assert captured["builtin_tools"] == []
    assert captured["subagents"] == [
        {
            "name": "rag_retriever",
            "description": "Runs semantic retrieval against internal wiki chunks.",
            "prompt": (
                "You are the retrieval subagent. Use the search_database tool to run similarity "
                "search over internal data and return concise, grounded findings from retrieved content."
            ),
            "tools": ["search_database"],
        }
    ]
    assert store.calls == [{"query": "strait of hormuz", "k": 1, "filter": None}]
    assert "Answer based on retrieval:" in result["messages"][-1].content
    assert "Hormuz shipping chokepoint summary." in result["messages"][-1].content
    assert "Coordinator agent invoke start subagent=rag_retriever" in caplog.text
    assert "Retriever tool search_database" in caplog.text
