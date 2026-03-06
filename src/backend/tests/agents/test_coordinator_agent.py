import logging
import sys
from pathlib import Path
from types import SimpleNamespace

from deepagents.backends import StateBackend
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

    def fake_create_deep_agent(*, model, tools, system_prompt, subagents, backend):
        captured["model"] = model
        captured["tools"] = tools
        captured["system_prompt"] = system_prompt
        captured["subagents"] = subagents
        captured["backend"] = backend
        # Retriever is on the subagent only; main agent has no tools.
        retriever = subagents[0]["tools"][0]
        return _FakeDeepAgent(retriever)

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
    assert captured["tools"] == []
    assert captured["backend"] == StateBackend
    assert "Call write_todos at the beginning to seed all pipeline stages" in str(captured["system_prompt"])
    assert "Use read_file and write_file" in str(captured["system_prompt"])
    assert "Create /runtime/coordinator_flow.md once with write_file, then use read_file + edit_file for updates." in str(
        captured["system_prompt"]
    )
    assert "Do not call write_file on an existing file path." in str(captured["system_prompt"])
    assert "/runtime/coordinator_flow.md" in str(captured["system_prompt"])
    assert "The user message will provide the exact initial sub-questions." in str(captured["system_prompt"])
    assert "Do not decompose again in this same context window." in str(captured["system_prompt"])
    assert "Delegate each provided sub-question via task(description=<exact sub-question>)." in str(
        captured["system_prompt"]
    )
    assert "Preserve the provided order and trailing '?'" in str(captured["system_prompt"])
    assert "For each initial sub-question (parallel): Expand -> Search -> Validate -> Rerank -> Answer -> Check." in str(
        captured["system_prompt"]
    )
    assert "Confirm delegation complete and subagent responses are gathered for handoff." in str(
        captured["system_prompt"]
    )
    assert "Do not synthesize or output the final answer to the main question." in str(captured["system_prompt"])
    assert "Delegation complete; subanswers collected." in str(captured["system_prompt"])
    assert len(captured["subagents"]) == 1
    sub = captured["subagents"][0]
    assert sub["name"] == "rag_retriever"
    assert sub["description"] == "This agent is a RAG subagent which answers each sub-question using the retriever tool."
    assert "You are the retrieval subagent." in sub["system_prompt"]
    assert "Retriever tool contract (search_database):" in sub["system_prompt"]
    assert "Call search_database with query=<exact subquestion> and expanded_query=<expanded query>." in sub["system_prompt"]
    assert "Return your response in this format: {subquestion}: {answer}" in sub["system_prompt"]
    assert len(sub["tools"]) == 1 and sub["tools"][0].name == "search_database"
    assert store.calls == [{"query": "strait of hormuz", "k": 1, "filter": None}]
    assert "Answer based on retrieval:" in result["messages"][-1].content
    assert "Hormuz shipping chokepoint summary." in result["messages"][-1].content
    assert "Coordinator agent invoke start subagent=rag_retriever" in caplog.text
    assert "backend=StateBackend" in caplog.text
    assert "final_message_only=true" in caplog.text
    assert "contract=co_located_retriever_and_response_format" in caplog.text


def test_create_coordinator_agent_accepts_backend_override() -> None:
    captured: dict[str, object] = {}

    class _FakeDeepAgent:
        def invoke(self, payload):
            return {"messages": [SimpleNamespace(content="ok")]}

    def fake_create_deep_agent(*, model, tools, system_prompt, subagents, backend):
        captured["backend"] = backend
        return _FakeDeepAgent()

    class _CustomBackend:
        pass

    agent = create_coordinator_agent(
        vector_store=_FakeVectorStore(),
        model="fake-model",
        create_deep_agent_fn=fake_create_deep_agent,
        backend_factory=_CustomBackend,
    )

    assert hasattr(agent, "invoke")
    assert captured["backend"] == _CustomBackend
