import logging
import sys
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schemas import RuntimeAgentRunRequest
from services import agent_service


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return Session(engine)


def test_extract_sub_qa_extracts_all_fields_from_tool_and_followup_messages() -> None:
    messages = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_task_1",
                    "name": "task",
                    "args": {"description": "What changed in policy X?", "subagent_type": "rag_retriever"},
                }
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_sd_1",
                    "name": "search_database",
                    "args": {"query": "What changed in policy X?", "limit": 10},
                }
            ],
        ),
        ToolMessage(content="Policy X was updated in 2024.", tool_call_id="call_sd_1", name="search_database"),
        AIMessage(content="Subagent final response for delegated policy question."),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_task_2",
                    "name": "task",
                    "args": {"description": "Synthesize a final user answer", "subagent_type": "rag_retriever"},
                }
            ],
        ),
    ]

    result = agent_service._extract_sub_qa(messages)

    assert len(result) == 1
    assert result[0].sub_question == "What changed in policy X?"
    assert result[0].sub_answer == "Policy X was updated in 2024."
    assert result[0].tool_call_input == '{"query": "What changed in policy X?", "limit": 10}'
    assert result[0].sub_agent_response == "Subagent final response for delegated policy question."


def test_extract_sub_qa_uses_last_ai_message_as_sub_agent_response() -> None:
    messages = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_task_1",
                    "name": "task",
                    "args": {"description": "Summarize the latest internal incident notes", "subagent_type": "rag_retriever"},
                }
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_sd_1",
                    "name": "search_database",
                    "args": {"query": "Summarize the latest internal incident notes", "limit": 10},
                }
            ],
        ),
        ToolMessage(content="Incident notes retrieved.", tool_call_id="call_sd_1", name="search_database"),
        AIMessage(content="Interim thought from subagent."),
        AIMessage(content="Final subagent answer for this delegated question."),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "id": "call_task_2",
                    "name": "task",
                    "args": {"description": "Draft final synthesis", "subagent_type": "rag_retriever"},
                }
            ],
        ),
        AIMessage(content="Main-agent synthesis that should not be captured for call_1."),
    ]

    result = agent_service._extract_sub_qa(messages)

    assert len(result) == 1
    assert result[0].sub_agent_response == "Final subagent answer for this delegated question."


def test_run_runtime_agent_returns_last_message_output_and_logs(monkeypatch, caplog) -> None:
    captured: dict[str, object] = {}

    class _FakeAgent:
        def invoke(self, payload, **kwargs):
            captured["payload"] = payload
            captured["config"] = kwargs.get("config")
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_task_1",
                                "name": "task",
                                "args": {"description": "What happened in NATO policy?", "subagent_type": "rag_retriever"},
                            }
                        ],
                    ),
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_sd_1",
                                "name": "search_database",
                                "args": {"query": "What happened in NATO policy?", "limit": 10},
                            }
                        ],
                    ),
                    ToolMessage(content="Policy shifted in 2025.", tool_call_id="call_sd_1", name="search_database"),
                    AIMessage(content="Subagent completed the delegated lookup."),
                    AIMessage(content="Final output"),
                ]
            }

    def fake_get_vector_store(*, connection: str, collection_name: str, embeddings):
        captured["connection"] = connection
        captured["collection_name"] = collection_name
        captured["embeddings"] = embeddings
        return "fake-vector-store"

    def fake_create_coordinator_agent(*, vector_store, model):
        captured["vector_store"] = vector_store
        captured["model"] = model
        return _FakeAgent()

    def fake_search_documents_for_context(*, vector_store, query, k, score_threshold):
        captured["context_search"] = {
            "vector_store": vector_store,
            "query": query,
            "k": k,
            "score_threshold": score_threshold,
        }
        return ["doc-a", "doc-b"]

    def fake_build_initial_search_context(documents):
        captured["context_docs"] = list(documents)
        return [
            {
                "rank": 1,
                "document_id": "doc-a",
                "title": "NATO",
                "source": "https://example.com/nato",
                "snippet": "NATO policy changed in 2025.",
            }
        ]

    monkeypatch.setattr(agent_service, "get_vector_store", fake_get_vector_store)
    monkeypatch.setattr(agent_service, "create_coordinator_agent", fake_create_coordinator_agent)
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", fake_search_documents_for_context)
    monkeypatch.setattr(agent_service, "build_initial_search_context", fake_build_initial_search_context)

    with caplog.at_level(logging.INFO):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="What happened in NATO policy?"),
            db=_make_session(),
        )

    assert response.output == "Final output"
    assert response.main_question == "What happened in NATO policy?"
    assert len(response.sub_qa) == 1
    assert response.sub_qa[0].sub_question == "What happened in NATO policy?"
    assert response.sub_qa[0].sub_answer == "Policy shifted in 2025."
    assert response.sub_qa[0].tool_call_input == '{"query": "What happened in NATO policy?", "limit": 10}'
    assert response.sub_qa[0].sub_agent_response == "Final output"
    assert captured["vector_store"] == "fake-vector-store"
    assert captured["collection_name"] == "agent_search_internal_data"
    assert captured["model"] == "gpt-4.1-mini"
    assert captured["context_search"]["query"] == "What happened in NATO policy?"
    assert captured["context_search"]["vector_store"] == "fake-vector-store"
    assert captured["context_search"]["k"] == agent_service._INITIAL_SEARCH_CONTEXT_K
    assert captured["context_docs"] == ["doc-a", "doc-b"]
    coordinator_message = captured["payload"]["messages"][0].content
    assert "User question:" in coordinator_message
    assert "What happened in NATO policy?" in coordinator_message
    assert "Initial retrieval context for decomposition" in coordinator_message
    assert '"title": "NATO"' in coordinator_message
    assert "Runtime agent run start" in caplog.text
    assert "Initial decomposition context built" in caplog.text
    assert "SubQuestionAnswer summary count=1" in caplog.text
    assert "SubQuestionAnswer[1]" in caplog.text and "What happened in NATO policy?" in caplog.text
    assert "Runtime agent run complete" in caplog.text
