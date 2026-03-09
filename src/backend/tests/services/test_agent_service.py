import logging
import sys
import time
import uuid
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schemas import DecomposeNodeInput, ExpandNodeInput, ExpandNodeOutput, RuntimeAgentRunRequest
from schemas.decomposition import DecompositionPlan
from services import document_validation_service
from services import agent_service


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return Session(engine)


def test_build_runtime_timeout_config_from_env_defaults(monkeypatch) -> None:
    keys = [
        "VECTOR_STORE_ACQUISITION_TIMEOUT_S",
        "INITIAL_SEARCH_TIMEOUT_S",
        "DECOMPOSITION_LLM_TIMEOUT_S",
        "COORDINATOR_INVOKE_TIMEOUT_S",
        "DOCUMENT_VALIDATION_TIMEOUT_S",
        "RERANK_TIMEOUT_S",
        "SUBANSWER_GENERATION_TIMEOUT_S",
        "SUBANSWER_VERIFICATION_TIMEOUT_S",
        "SUBQUESTION_PIPELINE_TOTAL_TIMEOUT_S",
        "INITIAL_ANSWER_TIMEOUT_S",
        "REFINEMENT_DECISION_TIMEOUT_S",
        "REFINEMENT_DECOMPOSITION_TIMEOUT_S",
        "REFINEMENT_RETRIEVAL_TIMEOUT_S",
        "REFINEMENT_PIPELINE_TOTAL_TIMEOUT_S",
        "REFINED_ANSWER_TIMEOUT_S",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)

    config = agent_service.build_runtime_timeout_config_from_env()

    assert config.vector_store_acquisition_timeout_s == 20
    assert config.initial_search_timeout_s == 20
    assert config.decomposition_llm_timeout_s == 60
    assert config.coordinator_invoke_timeout_s == 90
    assert config.document_validation_timeout_s == 20
    assert config.rerank_timeout_s == 20
    assert config.subanswer_generation_timeout_s == 60
    assert config.subanswer_verification_timeout_s == 30
    assert config.subquestion_pipeline_total_timeout_s == 120
    assert config.initial_answer_timeout_s == 60
    assert config.refinement_decision_timeout_s == 30
    assert config.refinement_decomposition_timeout_s == 60
    assert config.refinement_retrieval_timeout_s == 30
    assert config.refinement_pipeline_total_timeout_s == 120
    assert config.refined_answer_timeout_s == 60


def test_build_runtime_timeout_config_from_env_overrides_and_invalid_values(monkeypatch, caplog) -> None:
    monkeypatch.setenv("VECTOR_STORE_ACQUISITION_TIMEOUT_S", "11")
    monkeypatch.setenv("INITIAL_SEARCH_TIMEOUT_S", "12")
    monkeypatch.setenv("DECOMPOSITION_LLM_TIMEOUT_S", "13")
    monkeypatch.setenv("COORDINATOR_INVOKE_TIMEOUT_S", "14")
    monkeypatch.setenv("DOCUMENT_VALIDATION_TIMEOUT_S", "15")
    monkeypatch.setenv("RERANK_TIMEOUT_S", "16")
    monkeypatch.setenv("SUBANSWER_GENERATION_TIMEOUT_S", "17")
    monkeypatch.setenv("SUBANSWER_VERIFICATION_TIMEOUT_S", "18")
    monkeypatch.setenv("SUBQUESTION_PIPELINE_TOTAL_TIMEOUT_S", "19")
    monkeypatch.setenv("INITIAL_ANSWER_TIMEOUT_S", "20")
    monkeypatch.setenv("REFINEMENT_DECISION_TIMEOUT_S", "21")
    monkeypatch.setenv("REFINEMENT_DECOMPOSITION_TIMEOUT_S", "22")
    monkeypatch.setenv("REFINEMENT_RETRIEVAL_TIMEOUT_S", "23")
    monkeypatch.setenv("REFINEMENT_PIPELINE_TOTAL_TIMEOUT_S", "24")
    monkeypatch.setenv("REFINED_ANSWER_TIMEOUT_S", "abc")

    with caplog.at_level(logging.WARNING):
        config = agent_service.build_runtime_timeout_config_from_env()

    assert config.vector_store_acquisition_timeout_s == 11
    assert config.initial_search_timeout_s == 12
    assert config.decomposition_llm_timeout_s == 13
    assert config.coordinator_invoke_timeout_s == 14
    assert config.document_validation_timeout_s == 15
    assert config.rerank_timeout_s == 16
    assert config.subanswer_generation_timeout_s == 17
    assert config.subanswer_verification_timeout_s == 18
    assert config.subquestion_pipeline_total_timeout_s == 19
    assert config.initial_answer_timeout_s == 20
    assert config.refinement_decision_timeout_s == 21
    assert config.refinement_decomposition_timeout_s == 22
    assert config.refinement_retrieval_timeout_s == 23
    assert config.refinement_pipeline_total_timeout_s == 24
    assert config.refined_answer_timeout_s == 60
    assert "Invalid timeout env value; using default env_key=REFINED_ANSWER_TIMEOUT_S" in caplog.text


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
                    "args": {
                        "query": "What changed in policy X?",
                        "expanded_query": "policy x updates revisions changes",
                        "limit": 10,
                    },
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
    assert (
        result[0].tool_call_input
        == '{"query": "What changed in policy X?", "expanded_query": "policy x updates revisions changes", "limit": 10}'
    )
    assert result[0].expanded_query == "policy x updates revisions changes"
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
    assert result[0].expanded_query == ""
    assert result[0].sub_agent_response == "Final subagent answer for this delegated question."


def test_run_runtime_agent_generates_initial_answer_and_logs(monkeypatch, caplog) -> None:
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

    def fake_generate_initial_answer(*, main_question, initial_search_context, sub_qa):
        captured["initial_answer_input"] = {
            "main_question": main_question,
            "initial_search_context": initial_search_context,
            "sub_qa_count": len(sub_qa),
        }
        return "Initial synthesized answer"

    def fake_run_decomposition_only_llm_call(*, query, initial_search_context, model=None):
        captured["decomposition_input"] = {
            "query": query,
            "initial_search_context": initial_search_context,
            "model": model,
        }
        return '["What changed in NATO policy", "Why did NATO policy change?"]'

    monkeypatch.setattr(agent_service, "get_vector_store", fake_get_vector_store)
    monkeypatch.setattr(agent_service, "create_coordinator_agent", fake_create_coordinator_agent)
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", fake_search_documents_for_context)
    monkeypatch.setattr(agent_service, "build_initial_search_context", fake_build_initial_search_context)
    monkeypatch.setattr(agent_service, "_run_decomposition_only_llm_call", fake_run_decomposition_only_llm_call)
    monkeypatch.setattr(agent_service, "generate_initial_answer", fake_generate_initial_answer)
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: "Generated subanswer from reranked docs.",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )

    with caplog.at_level(logging.INFO):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="What happened in NATO policy?"),
            db=_make_session(),
        )

    assert response.output == "Initial synthesized answer"
    assert response.main_question == "What happened in NATO policy?"
    assert len(response.sub_qa) == 1
    assert response.sub_qa[0].sub_question == "What happened in NATO policy?"
    assert response.sub_qa[0].sub_answer == "Generated subanswer from reranked docs."
    assert response.sub_qa[0].tool_call_input == '{"query": "What happened in NATO policy?", "limit": 10}'
    assert response.sub_qa[0].expanded_query == ""
    assert response.sub_qa[0].sub_agent_response == "Final output"
    assert response.sub_qa[0].answerable is True
    assert response.sub_qa[0].verification_reason == "grounded_in_reranked_documents"
    assert captured["vector_store"] == "fake-vector-store"
    assert captured["collection_name"] == "agent_search_internal_data"
    assert captured["model"] == "gpt-4.1-mini"
    assert captured["context_search"]["query"] == "What happened in NATO policy?"
    assert captured["context_search"]["vector_store"] == "fake-vector-store"
    assert captured["context_search"]["k"] == agent_service._INITIAL_SEARCH_CONTEXT_K
    assert captured["context_docs"] == ["doc-a", "doc-b"]
    assert captured["decomposition_input"]["query"] == "What happened in NATO policy?"
    assert captured["decomposition_input"]["initial_search_context"][0]["title"] == "NATO"
    assert captured["decomposition_input"]["model"] is None
    assert captured["initial_answer_input"]["main_question"] == "What happened in NATO policy?"
    assert captured["initial_answer_input"]["sub_qa_count"] == 1
    assert captured["initial_answer_input"]["initial_search_context"][0]["title"] == "NATO"
    invoke_config = captured["config"]
    assert isinstance(invoke_config, dict)
    assert "callbacks" in invoke_config
    assert isinstance(invoke_config.get("configurable"), dict)
    thread_id = invoke_config["configurable"].get("thread_id")
    assert isinstance(thread_id, str) and thread_id
    assert str(uuid.UUID(thread_id)) == thread_id
    coordinator_message = captured["payload"]["messages"][0].content
    assert "Provided sub-questions for delegation:" in coordinator_message
    assert '"What changed in NATO policy?"' in coordinator_message
    assert '"Why did NATO policy change?"' in coordinator_message
    assert "Delegation requirements:" in coordinator_message
    assert "Delegate each provided sub-question via task(description=<exact sub-question>)." in coordinator_message
    assert "Do not create new decomposition sub-questions" in coordinator_message
    assert "Runtime agent run start" in caplog.text
    assert "Initial decomposition context built" in caplog.text
    assert "Decomposition-only LLM output captured" in caplog.text
    assert "Decomposition output parsed sub_question_count=2" in caplog.text
    assert "Coordinator sub-question input prepared parsed_sub_questions=2" in caplog.text


def test_run_runtime_agent_uses_provided_model_for_coordinator_and_decomposition(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {
                "messages": [
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
                    ToolMessage(content="Policy X evidence.", tool_call_id="call_sd_1", name="search_database"),
                    AIMessage(content="Subagent completed policy X."),
                    AIMessage(content="Coordinator output"),
                ]
            }

    class _FakeProvidedModel:
        pass

    provided_model = _FakeProvidedModel()

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "create_coordinator_agent",
        lambda *, vector_store, model: captured.update({"coordinator_model": model}) or _FakeAgent(),
    )

    def fake_run_decomposition_only_llm_call(*, query, initial_search_context, model=None):
        captured["decomposition_model"] = model
        return '["What changed in policy X?"]'

    monkeypatch.setattr(agent_service, "_run_decomposition_only_llm_call", fake_run_decomposition_only_llm_call)
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: "Initial synthesized output",
    )
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: "Generated subanswer from reranked docs.",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )

    response = agent_service.run_runtime_agent(
        RuntimeAgentRunRequest(query="What changed in policy X?"),
        db=_make_session(),
        model=provided_model,
    )

    assert response.output == "Initial synthesized output"
    assert captured["coordinator_model"] is provided_model
    assert captured["decomposition_model"] is provided_model


def test_run_runtime_agent_uses_provided_vector_store_for_search_coordinator_and_refinement(monkeypatch) -> None:
    captured: dict[str, object] = {"search_calls": []}

    class _FakeAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {
                "messages": [
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
                    ToolMessage(content="Policy X evidence.", tool_call_id="call_sd_1", name="search_database"),
                    AIMessage(content="Subagent completed policy X."),
                    AIMessage(content="Coordinator output"),
                ]
            }

    provided_vector_store = object()

    def fail_if_get_vector_store_called(**kwargs):
        raise AssertionError("get_vector_store should not be called when vector_store is provided")

    def fake_search_documents_for_context(*, vector_store, query, k, score_threshold):
        captured["search_calls"].append(
            {
                "vector_store": vector_store,
                "query": query,
                "k": k,
                "score_threshold": score_threshold,
            }
        )
        return []

    monkeypatch.setattr(agent_service, "get_vector_store", fail_if_get_vector_store_called)
    monkeypatch.setattr(agent_service, "search_documents_for_context", fake_search_documents_for_context)
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "create_coordinator_agent",
        lambda *, vector_store, model: captured.update({"coordinator_vector_store": vector_store}) or _FakeAgent(),
    )
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["What changed in policy X?"]',
    )
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: (
            "Initial synthesized output"
            if len(initial_search_context) == 0 and len(sub_qa) == 1 and sub_qa[0].sub_question == "What changed in policy X?"
            else "Refined synthesized output"
        ),
    )
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: "Generated subanswer from reranked docs.",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=False,
            reason="insufficient_grounding",
        ),
    )
    monkeypatch.setattr(
        agent_service,
        "should_refine",
        lambda *, question, initial_answer, sub_qa: type(
            "Decision",
            (),
            {"refinement_needed": True, "reason": "low_answerable_ratio"},
        )(),
    )
    monkeypatch.setattr(
        agent_service,
        "refine_subquestions",
        lambda *, question, initial_answer, sub_qa: ["Which source confirms policy X changes?"],
    )

    response = agent_service.run_runtime_agent(
        RuntimeAgentRunRequest(query="What changed in policy X?"),
        db=_make_session(),
        vector_store=provided_vector_store,
    )

    assert response.output == "Refined synthesized output"
    assert captured["coordinator_vector_store"] is provided_vector_store
    assert len(captured["search_calls"]) >= 2
    assert captured["search_calls"][0]["query"] == "What changed in policy X?"
    assert captured["search_calls"][0]["vector_store"] is provided_vector_store
    assert captured["search_calls"][1]["query"] == "Which source confirms policy X changes?"
    assert captured["search_calls"][1]["vector_store"] is provided_vector_store


def test_run_runtime_agent_times_out_while_acquiring_default_vector_store(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=1,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    def slow_get_vector_store(**kwargs):
        _ = kwargs
        time.sleep(1.2)
        return "slow-vector-store"

    monkeypatch.setattr(agent_service, "get_vector_store", slow_get_vector_store)
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(
        agent_service,
        "create_coordinator_agent",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("coordinator should not be created on timeout")),
    )

    with caplog.at_level(logging.WARNING):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="Will this timeout?"),
            db=_make_session(),
        )

    assert response.main_question == "Will this timeout?"
    assert response.sub_qa == []
    assert response.output == agent_service._VECTOR_STORE_TIMEOUT_FALLBACK_MESSAGE
    assert "Runtime guardrail timeout operation=vector_store_acquisition timeout_s=1" in caplog.text
    assert "Runtime agent short-circuiting due to vector store timeout" in caplog.text


def test_run_runtime_agent_acquires_default_vector_store_without_timeout(monkeypatch) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=2,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    captured: dict[str, object] = {}

    class _FakeAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {
                "messages": [
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
                    ToolMessage(content="Policy X evidence.", tool_call_id="call_sd_1", name="search_database"),
                    AIMessage(content="Subagent completed policy X."),
                    AIMessage(content="Coordinator output"),
                ]
            }

    def fast_get_vector_store(**kwargs):
        _ = kwargs
        time.sleep(0.1)
        return "fast-vector-store"

    monkeypatch.setattr(agent_service, "get_vector_store", fast_get_vector_store)
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["What changed in policy X?"]',
    )
    monkeypatch.setattr(
        agent_service,
        "create_coordinator_agent",
        lambda *, vector_store, model: captured.update({"vector_store": vector_store}) or _FakeAgent(),
    )
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: "Initial synthesized output",
    )
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: "Generated subanswer from reranked docs.",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )

    response = agent_service.run_runtime_agent(
        RuntimeAgentRunRequest(query="What changed in policy X?"),
        db=_make_session(),
    )

    assert response.output == "Initial synthesized output"
    assert captured["vector_store"] == "fast-vector-store"


def test_run_runtime_agent_continues_with_empty_initial_context_on_initial_search_timeout(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=1,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    captured: dict[str, object] = {}

    class _FakeAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {
                "messages": [
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
                    ToolMessage(content="Policy X evidence.", tool_call_id="call_sd_1", name="search_database"),
                    AIMessage(content="Subagent completed policy X."),
                    AIMessage(content="Coordinator output"),
                ]
            }

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")

    def slow_search_documents_for_context(**kwargs):
        _ = kwargs
        time.sleep(1.2)
        return ["doc-a"]

    monkeypatch.setattr(agent_service, "search_documents_for_context", slow_search_documents_for_context)
    monkeypatch.setattr(
        agent_service,
        "build_initial_search_context",
        lambda documents: (_ for _ in ()).throw(AssertionError("build_initial_search_context should not run on timeout")),
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FakeAgent())

    def fake_decomposition_call(*, query, initial_search_context, model=None):
        captured["decomposition_context"] = initial_search_context
        _ = query, model
        return '["What changed in policy X?"]'

    monkeypatch.setattr(agent_service, "_run_decomposition_only_llm_call", fake_decomposition_call)

    def fake_generate_initial_answer(*, main_question, initial_search_context, sub_qa):
        captured["initial_answer_context"] = initial_search_context
        _ = main_question, sub_qa
        return "Initial synthesized output"

    monkeypatch.setattr(agent_service, "generate_initial_answer", fake_generate_initial_answer)
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: "Generated subanswer from reranked docs.",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )

    with caplog.at_level(logging.WARNING):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="What changed in policy X?"),
            db=_make_session(),
        )

    assert response.output == "Initial synthesized output"
    assert captured["decomposition_context"] == []
    assert captured["initial_answer_context"] == []
    assert "Runtime guardrail timeout operation=initial_search_context_build timeout_s=1" in caplog.text
    assert "Initial decomposition context timeout; continuing with empty context" in caplog.text


def test_run_runtime_agent_builds_initial_context_when_initial_search_completes_within_timeout(monkeypatch) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=2,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    captured: dict[str, object] = {}

    class _FakeAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {
                "messages": [
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
                    ToolMessage(content="Policy X evidence.", tool_call_id="call_sd_1", name="search_database"),
                    AIMessage(content="Subagent completed policy X."),
                    AIMessage(content="Coordinator output"),
                ]
            }

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")

    def fast_search_documents_for_context(**kwargs):
        _ = kwargs
        time.sleep(0.1)
        return ["doc-a"]

    monkeypatch.setattr(agent_service, "search_documents_for_context", fast_search_documents_for_context)
    monkeypatch.setattr(
        agent_service,
        "build_initial_search_context",
        lambda documents: [{"rank": 1, "title": "Doc A"}] if documents else [],
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FakeAgent())

    def fake_decomposition_call(*, query, initial_search_context, model=None):
        captured["decomposition_context"] = initial_search_context
        _ = query, model
        return '["What changed in policy X?"]'

    monkeypatch.setattr(agent_service, "_run_decomposition_only_llm_call", fake_decomposition_call)

    def fake_generate_initial_answer(*, main_question, initial_search_context, sub_qa):
        captured["initial_answer_context"] = initial_search_context
        _ = main_question, sub_qa
        return "Initial synthesized output"

    monkeypatch.setattr(agent_service, "generate_initial_answer", fake_generate_initial_answer)
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: "Generated subanswer from reranked docs.",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )

    response = agent_service.run_runtime_agent(
        RuntimeAgentRunRequest(query="What changed in policy X?"),
        db=_make_session(),
    )

    assert response.output == "Initial synthesized output"
    assert captured["decomposition_context"] == [{"rank": 1, "title": "Doc A"}]
    assert captured["initial_answer_context"] == [{"rank": 1, "title": "Doc A"}]


def test_run_runtime_agent_uses_fallback_subquestion_on_decomposition_timeout(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=1,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    captured: dict[str, object] = {}

    class _FakeAgent:
        def invoke(self, payload, **kwargs):
            captured["coordinator_message"] = payload["messages"][0].content
            _ = kwargs
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_task_1",
                                "name": "task",
                                "args": {"description": "Explain policy x?", "subagent_type": "rag_retriever"},
                            }
                        ],
                    ),
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_sd_1",
                                "name": "search_database",
                                "args": {"query": "Explain policy x?", "limit": 10},
                            }
                        ],
                    ),
                    ToolMessage(content="Policy X evidence.", tool_call_id="call_sd_1", name="search_database"),
                    AIMessage(content="Subagent completed policy X."),
                    AIMessage(content="Coordinator output"),
                ]
            }

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])

    def slow_decomposition_call(*, query, initial_search_context, model=None):
        _ = query, initial_search_context, model
        time.sleep(1.2)
        return '["slow response"]'

    monkeypatch.setattr(agent_service, "_run_decomposition_only_llm_call", slow_decomposition_call)
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FakeAgent())
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: "Initial synthesized output",
    )
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: "Generated subanswer from reranked docs.",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )

    with caplog.at_level(logging.WARNING):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="Explain policy x"),
            db=_make_session(),
        )

    assert response.output == "Initial synthesized output"
    assert '"Explain policy x?"' in captured["coordinator_message"]
    assert "Runtime guardrail timeout operation=decomposition_llm_call timeout_s=1" in caplog.text
    assert "Decomposition LLM timeout; continuing with fallback sub-question" in caplog.text


def test_run_runtime_agent_uses_decomposition_output_when_call_completes_within_timeout(monkeypatch) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=2,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    captured: dict[str, object] = {}

    class _FakeAgent:
        def invoke(self, payload, **kwargs):
            captured["coordinator_message"] = payload["messages"][0].content
            _ = kwargs
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_task_1",
                                "name": "task",
                                "args": {"description": "Custom decomposition question?", "subagent_type": "rag_retriever"},
                            }
                        ],
                    ),
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_sd_1",
                                "name": "search_database",
                                "args": {"query": "Custom decomposition question?", "limit": 10},
                            }
                        ],
                    ),
                    ToolMessage(content="Policy X evidence.", tool_call_id="call_sd_1", name="search_database"),
                    AIMessage(content="Subagent completed policy X."),
                    AIMessage(content="Coordinator output"),
                ]
            }

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])

    def fast_decomposition_call(*, query, initial_search_context, model=None):
        _ = query, initial_search_context, model
        time.sleep(0.1)
        return '["Custom decomposition question?"]'

    monkeypatch.setattr(agent_service, "_run_decomposition_only_llm_call", fast_decomposition_call)
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FakeAgent())
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: "Initial synthesized output",
    )
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: "Generated subanswer from reranked docs.",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )

    response = agent_service.run_runtime_agent(
        RuntimeAgentRunRequest(query="Explain policy x"),
        db=_make_session(),
    )

    assert response.output == "Initial synthesized output"
    assert '"Custom decomposition question?"' in captured["coordinator_message"]


def test_run_runtime_agent_uses_fallback_sub_qa_on_coordinator_timeout(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=1,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    class _SlowAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            time.sleep(1.2)
            return {"messages": [AIMessage(content="Late coordinator output")]}

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["Explain policy x?"]',
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _SlowAgent())
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: "Initial synthesized output",
    )
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: f"generated:{sub_question}",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )

    with caplog.at_level(logging.WARNING):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="Explain policy x"),
            db=_make_session(),
        )

    assert response.output == "Initial synthesized output"
    assert len(response.sub_qa) == 1
    assert response.sub_qa[0].sub_question == "Explain policy x?"
    assert response.sub_qa[0].sub_answer == "generated:Explain policy x?"
    assert "Runtime guardrail timeout operation=coordinator_invoke timeout_s=1" in caplog.text
    assert "Coordinator invoke timeout; continuing with fallback sub_qa" in caplog.text


def test_run_runtime_agent_uses_coordinator_result_when_invoke_completes_within_timeout(monkeypatch) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=2,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    class _FastAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            time.sleep(0.1)
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_task_1",
                                "name": "task",
                                "args": {"description": "Coordinator question?", "subagent_type": "rag_retriever"},
                            }
                        ],
                    ),
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_sd_1",
                                "name": "search_database",
                                "args": {"query": "Coordinator question?", "limit": 10},
                            }
                        ],
                    ),
                    ToolMessage(content="Coordinator evidence.", tool_call_id="call_sd_1", name="search_database"),
                    AIMessage(content="Subagent completed coordinator question."),
                    AIMessage(content="Coordinator output"),
                ]
            }

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["Decomposition-only question?"]',
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FastAgent())
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: "Initial synthesized output",
    )
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: f"generated:{sub_question}",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )

    response = agent_service.run_runtime_agent(
        RuntimeAgentRunRequest(query="Explain policy x"),
        db=_make_session(),
    )

    assert response.output == "Initial synthesized output"
    assert len(response.sub_qa) == 1
    assert response.sub_qa[0].sub_question == "Coordinator question?"
    assert response.sub_qa[0].sub_answer == "generated:Coordinator question?"


def test_run_runtime_agent_uses_partial_fallback_when_initial_answer_times_out(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=1,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    captured: dict[str, object] = {}

    class _FastAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {"messages": [AIMessage(content="Coordinator output")]}

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["Subquestion A?"]',
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FastAgent())
    monkeypatch.setattr(
        agent_service,
        "_extract_sub_qa",
        lambda *args, **kwargs: [
            agent_service.SubQuestionAnswer(
                sub_question="Subquestion A?",
                sub_answer="Partial evidence from subanswer A.",
                tool_call_input='{"query":"Subquestion A?"}',
            )
        ],
    )
    monkeypatch.setattr(
        agent_service,
        "run_pipeline_for_subquestions_with_timeout",
        lambda *, sub_qa, total_timeout_s: sub_qa,
    )

    def slow_generate_initial_answer(*, main_question, initial_search_context, sub_qa):
        _ = main_question, initial_search_context, sub_qa
        time.sleep(1.2)
        return "This should not be returned"

    monkeypatch.setattr(agent_service, "generate_initial_answer", slow_generate_initial_answer)
    monkeypatch.setattr(
        agent_service,
        "should_refine",
        lambda *, question, initial_answer, sub_qa: captured.update({"decision_initial_answer": initial_answer}) or type(
            "Decision",
            (),
            {"refinement_needed": False, "reason": "fallback_used"},
        )(),
    )

    with caplog.at_level(logging.WARNING):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="Why did policy X change?"),
            db=_make_session(),
        )

    assert response.output.startswith(agent_service._INITIAL_ANSWER_TIMEOUT_FALLBACK_PREFIX)
    assert "Partial evidence from subanswer A." in response.output
    assert captured["decision_initial_answer"] == response.output
    assert "Runtime guardrail timeout operation=initial_answer_generation timeout_s=1" in caplog.text
    assert "Initial answer generation timeout; continuing with partial fallback" in caplog.text


def test_run_runtime_agent_uses_generated_initial_answer_when_within_timeout(monkeypatch) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=2,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    captured: dict[str, object] = {}

    class _FastAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {"messages": [AIMessage(content="Coordinator output")]}

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["Subquestion A?"]',
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FastAgent())
    monkeypatch.setattr(
        agent_service,
        "_extract_sub_qa",
        lambda *args, **kwargs: [
            agent_service.SubQuestionAnswer(
                sub_question="Subquestion A?",
                sub_answer="Evidence A",
                tool_call_input='{"query":"Subquestion A?"}',
            )
        ],
    )
    monkeypatch.setattr(
        agent_service,
        "run_pipeline_for_subquestions_with_timeout",
        lambda *, sub_qa, total_timeout_s: sub_qa,
    )
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: "Generated initial answer",
    )
    monkeypatch.setattr(
        agent_service,
        "should_refine",
        lambda *, question, initial_answer, sub_qa: captured.update({"decision_initial_answer": initial_answer}) or type(
            "Decision",
            (),
            {"refinement_needed": False, "reason": "enough_confidence"},
        )(),
    )

    response = agent_service.run_runtime_agent(
        RuntimeAgentRunRequest(query="Why did policy X change?"),
        db=_make_session(),
    )

    assert response.output == "Generated initial answer"
    assert captured["decision_initial_answer"] == "Generated initial answer"


def test_run_runtime_agent_skips_refinement_when_decision_times_out(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=1,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    class _FastAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {"messages": [AIMessage(content="Coordinator output")]}

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["Subquestion A?"]',
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FastAgent())
    monkeypatch.setattr(
        agent_service,
        "_extract_sub_qa",
        lambda *args, **kwargs: [
            agent_service.SubQuestionAnswer(
                sub_question="Subquestion A?",
                sub_answer="Evidence A",
                tool_call_input='{"query":"Subquestion A?"}',
            )
        ],
    )
    monkeypatch.setattr(
        agent_service,
        "run_pipeline_for_subquestions_with_timeout",
        lambda *, sub_qa, total_timeout_s: sub_qa,
    )
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: "Generated initial answer",
    )

    def slow_should_refine(*, question, initial_answer, sub_qa):
        _ = question, initial_answer, sub_qa
        time.sleep(1.2)
        return type("Decision", (), {"refinement_needed": True, "reason": "should_not_be_used"})()

    monkeypatch.setattr(agent_service, "should_refine", slow_should_refine)
    monkeypatch.setattr(
        agent_service,
        "refine_subquestions",
        lambda *, question, initial_answer, sub_qa: [
            "This should not run due to timeout fallback",
        ],
    )

    with caplog.at_level(logging.WARNING):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="Why did policy X change?"),
            db=_make_session(),
        )

    assert response.output == "Generated initial answer"
    assert len(response.sub_qa) == 1
    assert response.sub_qa[0].sub_question == "Subquestion A?"
    assert "Runtime guardrail timeout operation=refinement_decision timeout_s=1" in caplog.text
    assert "Refinement decision timeout; continuing without refinement" in caplog.text


def test_run_runtime_agent_skips_refinement_when_decomposition_times_out(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=1,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    class _FastAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {"messages": [AIMessage(content="Coordinator output")]}

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["Subquestion A?"]',
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FastAgent())
    monkeypatch.setattr(
        agent_service,
        "_extract_sub_qa",
        lambda *args, **kwargs: [
            agent_service.SubQuestionAnswer(
                sub_question="Subquestion A?",
                sub_answer="Evidence A",
                tool_call_input='{"query":"Subquestion A?"}',
            )
        ],
    )
    monkeypatch.setattr(
        agent_service,
        "run_pipeline_for_subquestions_with_timeout",
        lambda *, sub_qa, total_timeout_s: sub_qa,
    )
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: "Generated initial answer",
    )
    monkeypatch.setattr(
        agent_service,
        "should_refine",
        lambda *, question, initial_answer, sub_qa: type(
            "Decision",
            (),
            {"refinement_needed": True, "reason": "needs_refinement"},
        )(),
    )

    def slow_refine_subquestions(*, question, initial_answer, sub_qa):
        _ = question, initial_answer, sub_qa
        time.sleep(1.2)
        return ["This should not be used"]

    monkeypatch.setattr(agent_service, "refine_subquestions", slow_refine_subquestions)
    monkeypatch.setattr(
        agent_service,
        "_seed_refined_sub_qa_from_retrieval",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("refinement retrieval should not run on timeout")),
    )

    with caplog.at_level(logging.WARNING):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="Why did policy X change?"),
            db=_make_session(),
        )

    assert response.output == "Generated initial answer"
    assert len(response.sub_qa) == 1
    assert response.sub_qa[0].sub_question == "Subquestion A?"
    assert "Runtime guardrail timeout operation=refinement_decomposition timeout_s=1" in caplog.text
    assert "Refinement decomposition timeout; continuing with initial answer" in caplog.text


def test_run_runtime_agent_skips_refinement_when_retrieval_times_out(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=1,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    class _FastAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {"messages": [AIMessage(content="Coordinator output")]}

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["Subquestion A?"]',
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FastAgent())
    monkeypatch.setattr(
        agent_service,
        "_extract_sub_qa",
        lambda *args, **kwargs: [
            agent_service.SubQuestionAnswer(
                sub_question="Subquestion A?",
                sub_answer="Evidence A",
                tool_call_input='{"query":"Subquestion A?"}',
            )
        ],
    )
    monkeypatch.setattr(
        agent_service,
        "run_pipeline_for_subquestions_with_timeout",
        lambda *, sub_qa, total_timeout_s: sub_qa,
    )
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: "Generated initial answer",
    )
    monkeypatch.setattr(
        agent_service,
        "should_refine",
        lambda *, question, initial_answer, sub_qa: type(
            "Decision",
            (),
            {"refinement_needed": True, "reason": "needs_refinement"},
        )(),
    )
    monkeypatch.setattr(
        agent_service,
        "refine_subquestions",
        lambda *, question, initial_answer, sub_qa: ["Refined sub-question?"],
    )

    def slow_seed_refined_sub_qa_from_retrieval(*, vector_store, refined_subquestions):
        _ = vector_store, refined_subquestions
        time.sleep(1.2)
        return []

    monkeypatch.setattr(
        agent_service,
        "_seed_refined_sub_qa_from_retrieval",
        slow_seed_refined_sub_qa_from_retrieval,
    )
    monkeypatch.setattr(
        agent_service,
        "run_pipeline_for_subquestions",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("refinement pipeline should not run when refinement retrieval times out")
        ),
    )

    with caplog.at_level(logging.WARNING):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="Why did policy X change?"),
            db=_make_session(),
        )

    assert response.output == "Generated initial answer"
    assert len(response.sub_qa) == 1
    assert response.sub_qa[0].sub_question == "Subquestion A?"
    assert "Runtime guardrail timeout operation=refinement_retrieval timeout_s=1" in caplog.text
    assert "Refinement retrieval timeout; continuing with initial answer" in caplog.text
    assert "Refinement retrieval produced no seeded sub-questions; keeping initial answer output" in caplog.text


def test_run_runtime_agent_refinement_pipeline_timeout_returns_partial(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=5,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=1,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    class _FastAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {"messages": [AIMessage(content="Coordinator output")]}

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["Subquestion A?"]',
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FastAgent())
    monkeypatch.setattr(
        agent_service,
        "_extract_sub_qa",
        lambda *args, **kwargs: [
            agent_service.SubQuestionAnswer(
                sub_question="Subquestion A?",
                sub_answer="Initial evidence",
                tool_call_input='{"query":"Subquestion A?"}',
            )
        ],
    )
    monkeypatch.setattr(
        agent_service,
        "should_refine",
        lambda *, question, initial_answer, sub_qa: type(
            "Decision",
            (),
            {"refinement_needed": True, "reason": "needs_refinement"},
        )(),
    )
    monkeypatch.setattr(
        agent_service,
        "refine_subquestions",
        lambda *, question, initial_answer, sub_qa: ["Refined slow?", "Refined fast?"],
    )
    monkeypatch.setattr(
        agent_service,
        "_seed_refined_sub_qa_from_retrieval",
        lambda *, vector_store, refined_subquestions: [
            agent_service.SubQuestionAnswer(
                sub_question="Refined slow?",
                sub_answer="Slow evidence",
                tool_call_input='{"query":"Refined slow?"}',
            ),
            agent_service.SubQuestionAnswer(
                sub_question="Refined fast?",
                sub_answer="Fast evidence",
                tool_call_input='{"query":"Refined fast?"}',
            ),
        ],
    )

    def fake_single_pipeline(item: agent_service.SubQuestionAnswer) -> agent_service.SubQuestionAnswer:
        output = item.model_copy(deep=True)
        if output.sub_question == "Subquestion A?":
            time.sleep(0.1)
            output.sub_answer = "Initial processed answer"
            output.answerable = True
            output.verification_reason = "grounded_in_reranked_documents"
            return output
        if output.sub_question == "Refined slow?":
            time.sleep(1.2)
            output.sub_answer = "Refined slow processed"
            output.answerable = True
            output.verification_reason = "grounded_in_reranked_documents"
            return output
        time.sleep(0.1)
        output.sub_answer = "Refined fast processed"
        output.answerable = True
        output.verification_reason = "grounded_in_reranked_documents"
        return output

    monkeypatch.setattr(agent_service, "_run_pipeline_for_single_subquestion", fake_single_pipeline)

    def fake_generate_initial_answer(*, main_question, initial_search_context, sub_qa):
        _ = main_question, initial_search_context
        if sub_qa and sub_qa[0].sub_question.startswith("Refined"):
            return "Refined answer after partial pipeline"
        return "Initial answer"

    monkeypatch.setattr(agent_service, "generate_initial_answer", fake_generate_initial_answer)

    with caplog.at_level(logging.WARNING):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="Why did policy X change?"),
            db=_make_session(),
        )

    assert response.output == "Refined answer after partial pipeline"
    assert len(response.sub_qa) == 2
    assert response.sub_qa[0].sub_question == "Refined slow?"
    assert response.sub_qa[0].answerable is False
    assert response.sub_qa[0].verification_reason == "subquestion_pipeline_timed_out"
    assert response.sub_qa[1].sub_question == "Refined fast?"
    assert response.sub_qa[1].answerable is True
    assert response.sub_qa[1].verification_reason == "grounded_in_reranked_documents"
    assert "Per-subquestion pipeline total timeout; returning partial results" in caplog.text


def test_run_runtime_agent_refinement_pipeline_completes_within_timeout(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=5,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=2,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    class _FastAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {"messages": [AIMessage(content="Coordinator output")]}

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["Subquestion A?"]',
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FastAgent())
    monkeypatch.setattr(
        agent_service,
        "_extract_sub_qa",
        lambda *args, **kwargs: [
            agent_service.SubQuestionAnswer(
                sub_question="Subquestion A?",
                sub_answer="Initial evidence",
                tool_call_input='{"query":"Subquestion A?"}',
            )
        ],
    )
    monkeypatch.setattr(
        agent_service,
        "should_refine",
        lambda *, question, initial_answer, sub_qa: type(
            "Decision",
            (),
            {"refinement_needed": True, "reason": "needs_refinement"},
        )(),
    )
    monkeypatch.setattr(
        agent_service,
        "refine_subquestions",
        lambda *, question, initial_answer, sub_qa: ["Refined first?", "Refined second?"],
    )
    monkeypatch.setattr(
        agent_service,
        "_seed_refined_sub_qa_from_retrieval",
        lambda *, vector_store, refined_subquestions: [
            agent_service.SubQuestionAnswer(
                sub_question="Refined first?",
                sub_answer="First evidence",
                tool_call_input='{"query":"Refined first?"}',
            ),
            agent_service.SubQuestionAnswer(
                sub_question="Refined second?",
                sub_answer="Second evidence",
                tool_call_input='{"query":"Refined second?"}',
            ),
        ],
    )

    def fake_single_pipeline(item: agent_service.SubQuestionAnswer) -> agent_service.SubQuestionAnswer:
        output = item.model_copy(deep=True)
        time.sleep(0.1)
        output.sub_answer = f"processed::{output.sub_question}"
        output.answerable = True
        output.verification_reason = "grounded_in_reranked_documents"
        return output

    monkeypatch.setattr(agent_service, "_run_pipeline_for_single_subquestion", fake_single_pipeline)

    def fake_generate_initial_answer(*, main_question, initial_search_context, sub_qa):
        _ = main_question, initial_search_context
        if sub_qa and sub_qa[0].sub_question.startswith("Refined"):
            return "Refined answer complete"
        return "Initial answer"

    monkeypatch.setattr(agent_service, "generate_initial_answer", fake_generate_initial_answer)

    with caplog.at_level(logging.INFO):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="Why did policy X change?"),
            db=_make_session(),
        )

    assert response.output == "Refined answer complete"
    assert [item.sub_question for item in response.sub_qa] == ["Refined first?", "Refined second?"]
    assert all(item.answerable is True for item in response.sub_qa)
    assert all(item.verification_reason == "grounded_in_reranked_documents" for item in response.sub_qa)
    assert "Refinement per-subquestion pipeline start count=2 total_timeout_s=2" in caplog.text
    assert "Per-subquestion pipeline total timeout; returning partial results" not in caplog.text


def test_run_runtime_agent_keeps_initial_answer_when_refined_answer_generation_times_out(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=5,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=2,
            refined_answer_timeout_s=1,
        ),
    )

    class _FastAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {"messages": [AIMessage(content="Coordinator output")]}

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["Subquestion A?"]',
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FastAgent())
    monkeypatch.setattr(
        agent_service,
        "_extract_sub_qa",
        lambda *args, **kwargs: [
            agent_service.SubQuestionAnswer(
                sub_question="Subquestion A?",
                sub_answer="Initial evidence",
                tool_call_input='{"query":"Subquestion A?"}',
            )
        ],
    )
    monkeypatch.setattr(
        agent_service,
        "should_refine",
        lambda *, question, initial_answer, sub_qa: type(
            "Decision",
            (),
            {"refinement_needed": True, "reason": "needs_refinement"},
        )(),
    )
    monkeypatch.setattr(
        agent_service,
        "refine_subquestions",
        lambda *, question, initial_answer, sub_qa: ["Refined first?"],
    )
    monkeypatch.setattr(
        agent_service,
        "_seed_refined_sub_qa_from_retrieval",
        lambda *, vector_store, refined_subquestions: [
            agent_service.SubQuestionAnswer(
                sub_question="Refined first?",
                sub_answer="First evidence",
                tool_call_input='{"query":"Refined first?"}',
            )
        ],
    )
    monkeypatch.setattr(
        agent_service,
        "_run_pipeline_for_single_subquestion",
        lambda item: item.model_copy(update={"answerable": True, "verification_reason": "grounded_in_reranked_documents"}),
    )

    def fake_generate_initial_answer(*, main_question, initial_search_context, sub_qa):
        _ = main_question, initial_search_context
        if sub_qa and sub_qa[0].sub_question.startswith("Refined"):
            time.sleep(1.2)
            return "Refined answer should not be used"
        return "Initial answer"

    monkeypatch.setattr(agent_service, "generate_initial_answer", fake_generate_initial_answer)

    with caplog.at_level(logging.WARNING):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="Why did policy X change?"),
            db=_make_session(),
        )

    assert response.output == "Initial answer"
    assert [item.sub_question for item in response.sub_qa] == ["Refined first?"]
    assert "Runtime guardrail timeout operation=refined_answer_generation timeout_s=1" in caplog.text
    assert "Refined answer generation timeout; keeping initial answer" in caplog.text


def test_run_runtime_agent_continues_with_partial_sub_qa_on_total_pipeline_timeout(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=1,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    class _FastAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {"messages": [AIMessage(content="Coordinator output")]}

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda *, query, initial_search_context, model=None: '["Slow sub-question?", "Fast sub-question?"]',
    )
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FastAgent())
    monkeypatch.setattr(
        agent_service,
        "_extract_sub_qa",
        lambda *args, **kwargs: [
            agent_service.SubQuestionAnswer(
                sub_question="Slow sub-question?",
                sub_answer="1. title=Doc Slow source=wiki://slow content=slow evidence",
                tool_call_input='{"query":"Slow sub-question?"}',
            ),
            agent_service.SubQuestionAnswer(
                sub_question="Fast sub-question?",
                sub_answer="1. title=Doc Fast source=wiki://fast content=fast evidence",
                tool_call_input='{"query":"Fast sub-question?"}',
            ),
        ],
    )

    def fake_single_pipeline(item: agent_service.SubQuestionAnswer) -> agent_service.SubQuestionAnswer:
        output = item.model_copy(deep=True)
        if output.sub_question == "Slow sub-question?":
            time.sleep(1.2)
            output.sub_answer = "generated:slow"
            output.answerable = True
            output.verification_reason = "grounded_in_reranked_documents"
            return output
        time.sleep(0.1)
        output.sub_answer = "generated:fast"
        output.answerable = True
        output.verification_reason = "grounded_in_reranked_documents"
        return output

    monkeypatch.setattr(agent_service, "_run_pipeline_for_single_subquestion", fake_single_pipeline)
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: "Initial synthesized output",
    )
    monkeypatch.setattr(
        agent_service,
        "should_refine",
        lambda *, question, initial_answer, sub_qa: type(
            "Decision",
            (),
            {"refinement_needed": False, "reason": "enough_confidence"},
        )(),
    )

    with caplog.at_level(logging.WARNING):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="Explain policy x"),
            db=_make_session(),
        )

    assert response.output == "Initial synthesized output"
    assert len(response.sub_qa) == 2
    assert response.sub_qa[0].sub_question == "Slow sub-question?"
    assert response.sub_qa[0].sub_answer.startswith("1. title=Doc Slow")
    assert response.sub_qa[0].answerable is False
    assert response.sub_qa[0].verification_reason == "subquestion_pipeline_timed_out"
    assert response.sub_qa[1].sub_question == "Fast sub-question?"
    assert response.sub_qa[1].sub_answer == "generated:fast"
    assert response.sub_qa[1].answerable is True
    assert "Per-subquestion pipeline total timeout; returning partial results" in caplog.text


def test_run_runtime_agent_flags_refinement_path_when_decision_true(monkeypatch, caplog) -> None:
    captured: dict[str, object] = {}
    answer_calls: list[dict[str, object]] = []

    class _FakeAgent:
        def invoke(self, payload, **kwargs):
            _ = payload
            _ = kwargs
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_task_1",
                                "name": "task",
                                "args": {"description": "What changed in policy?", "subagent_type": "rag_retriever"},
                            }
                        ],
                    ),
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_sd_1",
                                "name": "search_database",
                                "args": {"query": "What changed in policy?", "limit": 10},
                            }
                        ],
                    ),
                    ToolMessage(content="No relevant evidence found.", tool_call_id="call_sd_1", name="search_database"),
                    AIMessage(content="Subagent could not ground an answer."),
                    AIMessage(content="Coordinator output"),
                ]
            }

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **_: "fake-vector-store")
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **_: _FakeAgent())
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **_: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: list(documents))

    def fake_generate_initial_answer(*, main_question, initial_search_context, sub_qa):
        answer_calls.append(
            {
                "main_question": main_question,
                "context_items": len(initial_search_context),
                "sub_qa_count": len(sub_qa),
            }
        )
        return "Initial answer with gaps" if len(answer_calls) == 1 else "Refined synthesized answer"

    monkeypatch.setattr(agent_service, "generate_initial_answer", fake_generate_initial_answer)
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: "No relevant docs were found.",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=False,
            reason="subanswer_reports_insufficient_evidence",
        ),
    )
    monkeypatch.setattr(
        agent_service,
        "should_refine",
        lambda *, question, initial_answer, sub_qa: type(
            "Decision",
            (),
            {"refinement_needed": True, "reason": "low_answerable_ratio:0.00"},
        )(),
    )
    def fake_refine_subquestions(*, question, initial_answer, sub_qa):
        captured["question"] = question
        captured["initial_answer"] = initial_answer
        captured["sub_qa_count"] = len(sub_qa)
        return [
            "What primary source evidence is missing for policy changes?",
            "Which dated policy updates can validate the claim?",
        ]

    monkeypatch.setattr(agent_service, "refine_subquestions", fake_refine_subquestions)

    with caplog.at_level(logging.INFO):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="What changed in policy?"),
            db=_make_session(),
        )

    assert response.output == "Refined synthesized answer"
    assert [item.sub_question for item in response.sub_qa] == [
        "What primary source evidence is missing for policy changes?",
        "Which dated policy updates can validate the claim?",
    ]
    assert captured["question"] == "What changed in policy?"
    assert captured["initial_answer"] == "Initial answer with gaps"
    assert captured["sub_qa_count"] == 1
    assert len(answer_calls) == 2
    assert answer_calls[0]["sub_qa_count"] == 1
    assert answer_calls[1]["sub_qa_count"] == 2
    assert "Refinement decision computed refinement_needed=True reason=low_answerable_ratio:0.00" in caplog.text
    assert "Refinement decomposition complete reason=low_answerable_ratio:0.00 refined_subquestion_count=2" in caplog.text
    assert "RefinedSubQuestion[1]=What primary source evidence is missing for policy changes?" in caplog.text
    assert "Refined sub-questions prepared for Section 14 handoff count=2" in caplog.text
    assert "Refinement answer generation completed within timeout timeout_s=" in caplog.text
    assert "SubQuestionAnswer summary count=2" in caplog.text
    assert "SubQuestionAnswer[1]" in caplog.text and "What primary source evidence is missing for policy changes?" in caplog.text
    assert "Coordinator raw output captured" in caplog.text
    assert "Runtime agent run complete" in caplog.text


def test_run_runtime_agent_includes_langfuse_callback_and_flushes(monkeypatch) -> None:
    captured: dict[str, object] = {"flushed_handler": None}

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
                                "args": {"description": "What changed in NATO policy?", "subagent_type": "rag_retriever"},
                            }
                        ],
                    ),
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_sd_1",
                                "name": "search_database",
                                "args": {"query": "What changed in NATO policy?", "limit": 10},
                            }
                        ],
                    ),
                    ToolMessage(content="Policy shifted in 2025.", tool_call_id="call_sd_1", name="search_database"),
                    AIMessage(content="Subagent completed the delegated lookup."),
                ]
            }

    class _FakeLangfuseCallback:
        pass

    langfuse_callback = _FakeLangfuseCallback()

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **_: "fake-vector-store")
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **_: _FakeAgent())
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **_: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: list(documents))
    monkeypatch.setattr(agent_service, "_run_decomposition_only_llm_call", lambda **_: '["What changed in NATO policy?"]')
    monkeypatch.setattr(agent_service, "generate_initial_answer", lambda **_: "Initial synthesized answer")
    monkeypatch.setattr(agent_service, "build_langfuse_callback_handler", lambda: langfuse_callback)
    monkeypatch.setattr(
        agent_service,
        "flush_langfuse_callback_handler",
        lambda handler: captured.__setitem__("flushed_handler", handler),
    )
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: "Generated subanswer from reranked docs.",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )

    _ = agent_service.run_runtime_agent(
        RuntimeAgentRunRequest(query="What happened in NATO policy?"),
        db=_make_session(),
    )

    invoke_config = captured["config"]
    assert isinstance(invoke_config, dict)
    callbacks = invoke_config.get("callbacks")
    assert isinstance(callbacks, list)
    assert langfuse_callback in callbacks
    assert captured["flushed_handler"] is langfuse_callback


def test_build_graph_run_metadata_defaults_to_run_id_for_trace_correlation_and_thread() -> None:
    metadata = agent_service.build_graph_run_metadata(run_id="run-123")

    assert metadata.run_id == "run-123"
    assert metadata.thread_id == "run-123"
    assert metadata.trace_id == "run-123"
    assert metadata.correlation_id == "run-123"


def test_build_agent_graph_state_keeps_compatibility_fields_and_subquestion_artifacts() -> None:
    sub_qa = [
        agent_service.SubQuestionAnswer(
            sub_question="What changed in policy X?",
            sub_answer="Policy X changed in 2025 [1].",
            expanded_query="policy x 2025 changes",
            tool_call_input='{"query":"policy x"}',
            sub_agent_response="subagent details",
            answerable=True,
            verification_reason="grounded_in_reranked_documents",
        )
    ]
    run_metadata = agent_service.build_graph_run_metadata(run_id="run-compat")

    state = agent_service.build_agent_graph_state(
        main_question="Summarize policy X changes.",
        decomposition_sub_questions=["What changed in policy X?"],
        sub_qa=sub_qa,
        final_answer="Policy X changed in 2025 [1].",
        run_metadata=run_metadata,
    )

    assert state.main_question == "Summarize policy X changes."
    assert state.decomposition_sub_questions == ["What changed in policy X?"]
    assert state.output == "Policy X changed in 2025 [1]."
    assert state.final_answer == "Policy X changed in 2025 [1]."
    assert len(state.sub_qa) == 1
    assert len(state.sub_question_artifacts) == 1
    assert state.sub_question_artifacts[0].expanded_queries == ["policy x 2025 changes"]
    assert state.citation_rows_by_index[1].content == "Policy X changed in 2025 [1]."
    assert state.run_metadata.run_id == "run-compat"
    assert state.run_metadata.trace_id == "run-compat"


def test_map_graph_state_to_runtime_response_is_backward_compatible() -> None:
    run_metadata = agent_service.build_graph_run_metadata(run_id="run-map")
    state = agent_service.build_agent_graph_state(
        main_question="Main question?",
        decomposition_sub_questions=["Sub-question?"],
        sub_qa=[
            agent_service.SubQuestionAnswer(
                sub_question="Sub-question?",
                sub_answer="sub-answer",
            )
        ],
        final_answer="final from graph",
        run_metadata=run_metadata,
    )
    state.output = ""

    response = agent_service.map_graph_state_to_runtime_response(state)

    assert response.main_question == "Main question?"
    assert response.output == "final from graph"
    assert len(response.sub_qa) == 1
    assert response.sub_qa[0].sub_question == "Sub-question?"


def test_build_coordinator_input_message_lists_provided_sub_questions_for_delegation() -> None:
    message = agent_service._build_coordinator_input_message(["What changed in VAT policy?"])

    assert "Provided sub-questions for delegation:" in message
    assert '["What changed in VAT policy?"]' in message
    assert "Delegation requirements:" in message
    assert "Delegate each provided sub-question via task(description=<exact sub-question>)." in message


def test_parse_decomposition_output_accepts_json_array_and_normalizes_questions() -> None:
    output = '["What changed in VAT policy", "What changed in VAT policy?", "Why did it change"]'

    parsed = agent_service._parse_decomposition_output(
        raw_output=output,
        query="Explain VAT changes",
    )

    assert parsed == [
        "What changed in VAT policy?",
        "Why did it change?",
    ]


def test_parse_decomposition_output_accepts_list_and_normalizes_questions() -> None:
    output = ["What changed in VAT policy", "What changed in VAT policy?", "Why did it change"]

    parsed = agent_service._parse_decomposition_output(
        raw_output=output,
        query="Explain VAT changes",
    )

    assert parsed == [
        "What changed in VAT policy?",
        "Why did it change?",
    ]


def test_parse_decomposition_output_accepts_decomposition_plan() -> None:
    output = DecompositionPlan(
        sub_questions=["What changed in VAT policy", "What changed in VAT policy?", "Why did it change"]
    )

    parsed = agent_service._parse_decomposition_output(
        raw_output=output,
        query="Explain VAT changes",
    )

    assert parsed == [
        "What changed in VAT policy?",
        "Why did it change?",
    ]


def test_parse_decomposition_output_accepts_newline_and_bullet_formats() -> None:
    output = """
    - What changed in VAT policy
    2. Which countries updated VAT rules?
    * When did VAT changes take effect
    """

    parsed = agent_service._parse_decomposition_output(
        raw_output=output,
        query="Explain VAT changes",
    )

    assert parsed == [
        "What changed in VAT policy?",
        "Which countries updated VAT rules?",
        "When did VAT changes take effect?",
    ]


def test_parse_decomposition_output_uses_fallback_when_malformed() -> None:
    parsed = agent_service._parse_decomposition_output(
        raw_output='{"unexpected":"shape"}',
        query="Explain VAT changes",
    )

    assert parsed == ["Explain VAT changes?"]


def test_parse_decomposition_output_uses_fallback_when_json_array_is_empty() -> None:
    parsed = agent_service._parse_decomposition_output(
        raw_output="[]",
        query="Explain VAT changes",
    )

    assert parsed == ["Explain VAT changes?"]


def test_run_decomposition_node_emits_normalized_subquestions(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_service,
        "_run_decomposition_only_llm_call",
        lambda **_: ["What changed in VAT policy", "what changed in vat policy?", "Why did it change"],
    )

    output = agent_service.run_decomposition_node(
        node_input=DecomposeNodeInput(
            main_question="Explain VAT changes",
            run_metadata=agent_service.build_graph_run_metadata(),
            initial_search_context=[{"rank": 1, "title": "VAT"}],
        ),
        timeout_s=5,
    )

    assert output.decomposition_sub_questions == [
        "What changed in VAT policy?",
        "Why did it change?",
    ]


def test_run_decomposition_node_uses_fallback_on_timeout(monkeypatch, caplog) -> None:
    def _raise_timeout(*, timeout_s: int, operation_name: str, fn):
        raise agent_service.FuturesTimeoutError()

    monkeypatch.setattr(agent_service, "_run_with_timeout", _raise_timeout)

    with caplog.at_level(logging.WARNING):
        output = agent_service.run_decomposition_node(
            node_input=DecomposeNodeInput(
                main_question="Explain VAT changes",
                run_metadata=agent_service.build_graph_run_metadata(),
                initial_search_context=[],
            ),
            timeout_s=1,
        )

    assert output.decomposition_sub_questions == ["Explain VAT changes?"]
    assert "Decomposition LLM timeout; continuing with fallback sub-question" in caplog.text


def test_run_expand_node_emits_bounded_query_list(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_service,
        "expand_queries_for_subquestion",
        lambda **_: ["What changed in VAT policy?", "VAT policy updates 2025", "VAT changes by region"],
    )

    output = agent_service.run_expand_node(
        node_input=ExpandNodeInput(
            main_question="Explain VAT changes",
            sub_question="What changed in VAT policy?",
            run_metadata=agent_service.build_graph_run_metadata(run_id="run-expand"),
        ),
    )

    assert output.expanded_queries == [
        "What changed in VAT policy?",
        "VAT policy updates 2025",
        "VAT changes by region",
    ]


def test_apply_expand_node_output_to_graph_state_updates_artifacts_and_compat_fields() -> None:
    state = agent_service.build_agent_graph_state(
        main_question="Explain VAT changes",
        decomposition_sub_questions=["What changed in VAT policy?"],
        sub_qa=[
            agent_service.SubQuestionAnswer(
                sub_question="What changed in VAT policy?",
                sub_answer="Sub answer.",
                expanded_query="",
            )
        ],
        final_answer="Sub answer.",
        run_metadata=agent_service.build_graph_run_metadata(run_id="run-expand-state"),
    )

    updated = agent_service.apply_expand_node_output_to_graph_state(
        state=state,
        sub_question="What changed in VAT policy?",
        node_output=ExpandNodeOutput(
            expanded_queries=[
                "What changed in VAT policy?",
                "VAT policy updates 2025",
                "VAT changes by region",
            ]
        ),
    )

    assert updated.sub_question_artifacts[0].expanded_queries == [
        "What changed in VAT policy?",
        "VAT policy updates 2025",
        "VAT changes by region",
    ]
    assert updated.sub_qa[0].expanded_query == "VAT policy updates 2025"


def test_extract_sub_qa_uses_callback_captured_search_calls() -> None:
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
        ToolMessage(content="Final delegated answer.", tool_call_id="call_task_1", name="task"),
    ]

    search_database_calls = [
        (
            '{"query":"What changed in policy X?","expanded_query":"policy x updates changes","limit":2}',
            "1. title=Policy X source=wiki://policy-x content=Policy X changed.\n2. title=Policy X Timeline source=wiki://policy-x-timeline content=Timeline details.",
        )
    ]

    result = agent_service._extract_sub_qa(messages, search_database_calls=search_database_calls)

    assert len(result) == 1
    assert result[0].sub_question == "What changed in policy X?"
    assert "1. title=Policy X" in result[0].sub_answer
    assert result[0].expanded_query == "policy x updates changes"
    assert result[0].sub_agent_response == "Final delegated answer."


def test_estimate_retrieved_doc_count_counts_ranked_lines() -> None:
    output = (
        "1. title=Alpha source=wiki://alpha content=A\n"
        "2. title=Beta source=wiki://beta content=B\n"
        "Not a numbered row"
    )

    assert agent_service._estimate_retrieved_doc_count(output) == 2


def test_format_retrieved_documents_for_pipeline_preserves_citation_contract_shape() -> None:
    class _Doc:
        def __init__(self, metadata: dict[str, str], page_content: str):
            self.metadata = metadata
            self.page_content = page_content

    output = agent_service._format_retrieved_documents_for_pipeline(
        [
            _Doc(
                metadata={"title": "NATO Policy", "source": "wiki://nato/policy"},
                page_content="Policy changed in 2025.",
            ),
            _Doc(
                metadata={"wiki_page": "Fallback Title", "wiki_url": "wiki://fallback"},
                page_content="Fallback source fields are used.",
            ),
        ]
    )

    assert output.splitlines() == [
        "1. title=NATO Policy source=wiki://nato/policy content=Policy changed in 2025.",
        "2. title=Fallback Title source=wiki://fallback content=Fallback source fields are used.",
    ]


def test_apply_document_validation_to_sub_qa_filters_documents(monkeypatch) -> None:
    input_sub_qa = [
        agent_service.SubQuestionAnswer(
            sub_question="What changed in NATO policy?",
            sub_answer="1. title=Doc A source=wiki://trusted content=Policy changed in 2025.\n2. title=Doc B source=wiki://other content=Other content.",
            tool_call_input='{"query":"What changed in NATO policy?","limit":2}',
            expanded_query="nato policy changes 2025",
            sub_agent_response="Delegated summary.",
        )
    ]

    doc_a = document_validation_service.RetrievedDocument(
        rank=1,
        title="Doc A",
        source="wiki://trusted",
        content="Policy changed in 2025.",
    )
    validation_result = document_validation_service.SubQuestionValidationResult(
        total_documents=2,
        valid_documents=[doc_a],
        validation_results=[],
    )

    def fake_validate_subquestion_documents(*, sub_question, retrieved_output, config):
        assert sub_question == "What changed in NATO policy?"
        assert "Doc A" in retrieved_output and "Doc B" in retrieved_output
        return validation_result

    monkeypatch.setattr(agent_service, "validate_subquestion_documents", fake_validate_subquestion_documents)

    output_sub_qa = agent_service._apply_document_validation_to_sub_qa(input_sub_qa)

    assert len(output_sub_qa) == 1
    assert output_sub_qa[0].sub_answer == "1. title=Doc A source=wiki://trusted content=Policy changed in 2025."


def test_apply_reranking_to_sub_qa_reorders_documents(monkeypatch) -> None:
    input_sub_qa = [
        agent_service.SubQuestionAnswer(
            sub_question="What changed in NATO policy?",
            sub_answer=(
                "1. title=General Update source=wiki://general content=Generic summary.\n"
                "2. title=NATO Policy Shift source=wiki://nato content=Policy changed in 2025."
            ),
            tool_call_input='{"query":"What changed in NATO policy?","expanded_query":"nato policy changes 2025","limit":2}',
            expanded_query="nato policy changes 2025",
            sub_agent_response="Delegated summary.",
        )
    ]

    output_sub_qa = agent_service._apply_reranking_to_sub_qa(input_sub_qa)

    assert len(output_sub_qa) == 1
    assert output_sub_qa[0].sub_answer.startswith("1. title=NATO Policy Shift")


def test_apply_subanswer_generation_to_sub_qa_uses_reranked_output(monkeypatch) -> None:
    input_sub_qa = [
        agent_service.SubQuestionAnswer(
            sub_question="What changed in NATO policy?",
            sub_answer="1. title=NATO source=wiki://nato content=Policy changed in 2025.",
            tool_call_input='{"query":"What changed in NATO policy?","limit":1}',
            expanded_query="nato policy changes 2025",
            sub_agent_response="Delegated summary.",
        )
    ]
    captured: dict[str, str] = {}

    def fake_generate_subanswer(*, sub_question: str, reranked_retrieved_output: str) -> str:
        captured["sub_question"] = sub_question
        captured["reranked_retrieved_output"] = reranked_retrieved_output
        return "Policy changed in 2025 (source: wiki://nato)."

    monkeypatch.setattr(agent_service, "generate_subanswer", fake_generate_subanswer)

    output_sub_qa = agent_service._apply_subanswer_generation_to_sub_qa(input_sub_qa)

    assert captured["sub_question"] == "What changed in NATO policy?"
    assert captured["reranked_retrieved_output"].startswith("1. title=NATO")
    assert output_sub_qa[0].sub_answer == "Policy changed in 2025 (source: wiki://nato)."


def test_apply_subanswer_verification_to_sub_qa_sets_answerable_and_reason(monkeypatch) -> None:
    input_sub_qa = [
        agent_service.SubQuestionAnswer(
            sub_question="What changed in NATO policy?",
            sub_answer="Policy changed in 2025 (source: wiki://nato).",
            tool_call_input='{"query":"What changed in NATO policy?","limit":1}',
            expanded_query="nato policy changes 2025",
            sub_agent_response="Delegated summary.",
        )
    ]
    captured: dict[str, str] = {}

    def fake_verify_subanswer(*, sub_question: str, sub_answer: str, reranked_retrieved_output: str):
        captured["sub_question"] = sub_question
        captured["sub_answer"] = sub_answer
        captured["reranked_retrieved_output"] = reranked_retrieved_output
        return agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        )

    monkeypatch.setattr(agent_service, "verify_subanswer", fake_verify_subanswer)

    output_sub_qa = agent_service._apply_subanswer_verification_to_sub_qa(
        input_sub_qa,
        reranked_output_by_sub_question={
            "What changed in NATO policy?": "1. title=NATO source=wiki://nato content=Policy changed in 2025."
        },
    )

    assert captured["sub_question"] == "What changed in NATO policy?"
    assert captured["sub_answer"] == "Policy changed in 2025 (source: wiki://nato)."
    assert captured["reranked_retrieved_output"].startswith("1. title=NATO")
    assert output_sub_qa[0].answerable is True
    assert output_sub_qa[0].verification_reason == "grounded_in_reranked_documents"


def test_run_pipeline_for_subquestions_runs_in_parallel_and_preserves_order(monkeypatch) -> None:
    input_sub_qa = [
        agent_service.SubQuestionAnswer(
            sub_question="Sub-question one?",
            sub_answer="retrieved docs one",
            tool_call_input='{"query":"Sub-question one?"}',
        ),
        agent_service.SubQuestionAnswer(
            sub_question="Sub-question two?",
            sub_answer="retrieved docs two",
            tool_call_input='{"query":"Sub-question two?"}',
        ),
    ]

    def fake_single_pipeline(item: agent_service.SubQuestionAnswer) -> agent_service.SubQuestionAnswer:
        time.sleep(0.2)
        output = item.model_copy(deep=True)
        output.sub_answer = f"generated:{item.sub_question}"
        output.answerable = True
        output.verification_reason = "grounded_in_reranked_documents"
        return output

    monkeypatch.setattr(agent_service, "_run_pipeline_for_single_subquestion", fake_single_pipeline)
    monkeypatch.setattr(agent_service, "_SUBQUESTION_PIPELINE_MAX_WORKERS", 2)

    start = time.perf_counter()
    output_sub_qa = agent_service.run_pipeline_for_subquestions(input_sub_qa)
    elapsed = time.perf_counter() - start

    assert len(output_sub_qa) == 2
    assert output_sub_qa[0].sub_question == "Sub-question one?"
    assert output_sub_qa[1].sub_question == "Sub-question two?"
    assert output_sub_qa[0].sub_answer == "generated:Sub-question one?"
    assert output_sub_qa[1].sub_answer == "generated:Sub-question two?"
    assert all(item.answerable is True for item in output_sub_qa)
    assert elapsed < 0.35


def test_run_pipeline_for_subquestions_with_timeout_returns_partial_and_marks_skipped(
    monkeypatch, caplog
) -> None:
    input_sub_qa = [
        agent_service.SubQuestionAnswer(
            sub_question="Slow sub-question?",
            sub_answer="1. title=Doc Slow source=wiki://slow content=slow evidence",
            tool_call_input='{"query":"Slow sub-question?"}',
        ),
        agent_service.SubQuestionAnswer(
            sub_question="Fast sub-question?",
            sub_answer="1. title=Doc Fast source=wiki://fast content=fast evidence",
            tool_call_input='{"query":"Fast sub-question?"}',
        ),
    ]

    def fake_single_pipeline(item: agent_service.SubQuestionAnswer) -> agent_service.SubQuestionAnswer:
        output = item.model_copy(deep=True)
        if output.sub_question == "Slow sub-question?":
            time.sleep(1.2)
            output.sub_answer = "generated:slow"
            output.answerable = True
            output.verification_reason = "grounded_in_reranked_documents"
            return output
        time.sleep(0.1)
        output.sub_answer = "generated:fast"
        output.answerable = True
        output.verification_reason = "grounded_in_reranked_documents"
        return output

    monkeypatch.setattr(agent_service, "_run_pipeline_for_single_subquestion", fake_single_pipeline)
    monkeypatch.setattr(agent_service, "_SUBQUESTION_PIPELINE_MAX_WORKERS", 2)

    with caplog.at_level(logging.WARNING):
        output_sub_qa = agent_service.run_pipeline_for_subquestions_with_timeout(
            sub_qa=input_sub_qa,
            total_timeout_s=1,
        )

    assert len(output_sub_qa) == 2
    assert output_sub_qa[0].sub_question == "Slow sub-question?"
    assert output_sub_qa[0].sub_answer.startswith("1. title=Doc Slow")
    assert output_sub_qa[0].answerable is False
    assert output_sub_qa[0].verification_reason == "subquestion_pipeline_timed_out"
    assert output_sub_qa[1].sub_question == "Fast sub-question?"
    assert output_sub_qa[1].sub_answer == "generated:fast"
    assert output_sub_qa[1].answerable is True
    assert "Per-subquestion pipeline total timeout; returning partial results" in caplog.text


def test_run_pipeline_for_single_subquestion_skips_document_validation_on_timeout(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=1,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    def slow_validation(sub_qa):
        time.sleep(1.2)
        return sub_qa

    def passthrough(sub_qa):
        return sub_qa

    monkeypatch.setattr(agent_service, "_apply_document_validation_to_sub_qa", slow_validation)
    monkeypatch.setattr(agent_service, "_apply_reranking_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_subanswer_generation_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_subanswer_verification_to_sub_qa", lambda sub_qa, **kwargs: sub_qa)

    input_item = agent_service.SubQuestionAnswer(
        sub_question="What changed in NATO policy?",
        sub_answer="1. title=Doc A source=wiki://a content=A",
        tool_call_input='{"query":"What changed in NATO policy?"}',
    )

    with caplog.at_level(logging.WARNING):
        output_item = agent_service._run_pipeline_for_single_subquestion(input_item)

    assert output_item.sub_answer == "1. title=Doc A source=wiki://a content=A"
    assert "Runtime guardrail timeout operation=document_validation_subquestion timeout_s=1" in caplog.text
    assert "Per-subquestion document validation timeout; continuing without validation" in caplog.text


def test_run_pipeline_for_single_subquestion_applies_document_validation_when_within_timeout(
    monkeypatch,
) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=2,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    def fast_validation(sub_qa):
        output = [item.model_copy(deep=True) for item in sub_qa]
        output[0].sub_answer = "validated output"
        return output

    def passthrough(sub_qa):
        return sub_qa

    monkeypatch.setattr(agent_service, "_apply_document_validation_to_sub_qa", fast_validation)
    monkeypatch.setattr(agent_service, "_apply_reranking_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_subanswer_generation_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_subanswer_verification_to_sub_qa", lambda sub_qa, **kwargs: sub_qa)

    input_item = agent_service.SubQuestionAnswer(
        sub_question="What changed in NATO policy?",
        sub_answer="1. title=Doc A source=wiki://a content=A",
        tool_call_input='{"query":"What changed in NATO policy?"}',
    )

    output_item = agent_service._run_pipeline_for_single_subquestion(input_item)

    assert output_item.sub_answer == "validated output"


def test_run_pipeline_for_single_subquestion_skips_reranking_on_timeout(monkeypatch, caplog) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=1,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    def passthrough(sub_qa):
        return sub_qa

    def slow_reranking(sub_qa):
        time.sleep(1.2)
        output = [item.model_copy(deep=True) for item in sub_qa]
        output[0].sub_answer = "reranked output"
        return output

    monkeypatch.setattr(agent_service, "_apply_document_validation_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_reranking_to_sub_qa", slow_reranking)
    monkeypatch.setattr(agent_service, "_apply_subanswer_generation_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_subanswer_verification_to_sub_qa", lambda sub_qa, **kwargs: sub_qa)

    input_item = agent_service.SubQuestionAnswer(
        sub_question="What changed in NATO policy?",
        sub_answer="1. title=Doc A source=wiki://a content=A",
        tool_call_input='{"query":"What changed in NATO policy?"}',
    )

    with caplog.at_level(logging.WARNING):
        output_item = agent_service._run_pipeline_for_single_subquestion(input_item)

    assert output_item.sub_answer == "1. title=Doc A source=wiki://a content=A"
    assert "Runtime guardrail timeout operation=rerank_subquestion timeout_s=1" in caplog.text
    assert "Per-subquestion reranking timeout; continuing with original document order" in caplog.text


def test_run_pipeline_for_single_subquestion_applies_reranking_when_within_timeout(monkeypatch) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=2,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    def passthrough(sub_qa):
        return sub_qa

    def fast_reranking(sub_qa):
        output = [item.model_copy(deep=True) for item in sub_qa]
        output[0].sub_answer = "reranked output"
        return output

    monkeypatch.setattr(agent_service, "_apply_document_validation_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_reranking_to_sub_qa", fast_reranking)
    monkeypatch.setattr(agent_service, "_apply_subanswer_generation_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_subanswer_verification_to_sub_qa", lambda sub_qa, **kwargs: sub_qa)

    input_item = agent_service.SubQuestionAnswer(
        sub_question="What changed in NATO policy?",
        sub_answer="1. title=Doc A source=wiki://a content=A",
        tool_call_input='{"query":"What changed in NATO policy?"}',
    )

    output_item = agent_service._run_pipeline_for_single_subquestion(input_item)

    assert output_item.sub_answer == "reranked output"


def test_run_pipeline_for_single_subquestion_uses_fallback_subanswer_on_generation_timeout(
    monkeypatch, caplog
) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=1,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    def passthrough(sub_qa):
        return sub_qa

    def slow_subanswer_generation(sub_qa):
        time.sleep(1.2)
        output = [item.model_copy(deep=True) for item in sub_qa]
        output[0].sub_answer = "generated output"
        return output

    monkeypatch.setattr(agent_service, "_apply_document_validation_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_reranking_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_subanswer_generation_to_sub_qa", slow_subanswer_generation)
    monkeypatch.setattr(agent_service, "_apply_subanswer_verification_to_sub_qa", lambda sub_qa, **kwargs: sub_qa)

    input_item = agent_service.SubQuestionAnswer(
        sub_question="What changed in NATO policy?",
        sub_answer="1. title=Doc A source=wiki://a content=A",
        tool_call_input='{"query":"What changed in NATO policy?"}',
    )

    with caplog.at_level(logging.WARNING):
        output_item = agent_service._run_pipeline_for_single_subquestion(input_item)

    assert output_item.sub_answer == "Answer not available in time."
    assert "Runtime guardrail timeout operation=subanswer_generation_subquestion timeout_s=1" in caplog.text
    assert "Per-subquestion subanswer generation timeout; continuing with fallback text" in caplog.text


def test_run_pipeline_for_single_subquestion_generates_subanswer_when_within_timeout(monkeypatch) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=2,
            subanswer_verification_timeout_s=original_config.subanswer_verification_timeout_s,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    def passthrough(sub_qa):
        return sub_qa

    def fast_subanswer_generation(sub_qa):
        output = [item.model_copy(deep=True) for item in sub_qa]
        output[0].sub_answer = "generated output"
        return output

    monkeypatch.setattr(agent_service, "_apply_document_validation_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_reranking_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_subanswer_generation_to_sub_qa", fast_subanswer_generation)
    monkeypatch.setattr(agent_service, "_apply_subanswer_verification_to_sub_qa", lambda sub_qa, **kwargs: sub_qa)

    input_item = agent_service.SubQuestionAnswer(
        sub_question="What changed in NATO policy?",
        sub_answer="1. title=Doc A source=wiki://a content=A",
        tool_call_input='{"query":"What changed in NATO policy?"}',
    )

    output_item = agent_service._run_pipeline_for_single_subquestion(input_item)

    assert output_item.sub_answer == "generated output"


def test_run_pipeline_for_single_subquestion_marks_unanswerable_on_verification_timeout(
    monkeypatch, caplog
) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=1,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    def passthrough(sub_qa):
        return sub_qa

    def slow_subanswer_verification(sub_qa, **kwargs):
        _ = kwargs
        time.sleep(1.2)
        return sub_qa

    monkeypatch.setattr(agent_service, "_apply_document_validation_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_reranking_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_subanswer_generation_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_subanswer_verification_to_sub_qa", slow_subanswer_verification)

    input_item = agent_service.SubQuestionAnswer(
        sub_question="What changed in NATO policy?",
        sub_answer="1. title=Doc A source=wiki://a content=A",
        tool_call_input='{"query":"What changed in NATO policy?"}',
    )

    with caplog.at_level(logging.WARNING):
        output_item = agent_service._run_pipeline_for_single_subquestion(input_item)

    assert output_item.answerable is False
    assert output_item.verification_reason == "verification_timed_out"
    assert "Runtime guardrail timeout operation=subanswer_verification_subquestion timeout_s=1" in caplog.text
    assert "Per-subquestion subanswer verification timeout; continuing with default unanswerable status" in caplog.text


def test_run_pipeline_for_single_subquestion_applies_verification_when_within_timeout(monkeypatch) -> None:
    original_config = agent_service._RUNTIME_TIMEOUT_CONFIG
    monkeypatch.setattr(
        agent_service,
        "_RUNTIME_TIMEOUT_CONFIG",
        agent_service.RuntimeTimeoutConfig(
            vector_store_acquisition_timeout_s=original_config.vector_store_acquisition_timeout_s,
            initial_search_timeout_s=original_config.initial_search_timeout_s,
            decomposition_llm_timeout_s=original_config.decomposition_llm_timeout_s,
            coordinator_invoke_timeout_s=original_config.coordinator_invoke_timeout_s,
            document_validation_timeout_s=original_config.document_validation_timeout_s,
            rerank_timeout_s=original_config.rerank_timeout_s,
            subanswer_generation_timeout_s=original_config.subanswer_generation_timeout_s,
            subanswer_verification_timeout_s=2,
            subquestion_pipeline_total_timeout_s=original_config.subquestion_pipeline_total_timeout_s,
            initial_answer_timeout_s=original_config.initial_answer_timeout_s,
            refinement_decision_timeout_s=original_config.refinement_decision_timeout_s,
            refinement_decomposition_timeout_s=original_config.refinement_decomposition_timeout_s,
            refinement_retrieval_timeout_s=original_config.refinement_retrieval_timeout_s,
            refinement_pipeline_total_timeout_s=original_config.refinement_pipeline_total_timeout_s,
            refined_answer_timeout_s=original_config.refined_answer_timeout_s,
        ),
    )

    def passthrough(sub_qa):
        return sub_qa

    def fast_subanswer_verification(sub_qa, **kwargs):
        _ = kwargs
        output = [item.model_copy(deep=True) for item in sub_qa]
        output[0].answerable = True
        output[0].verification_reason = "grounded_in_reranked_documents"
        return output

    monkeypatch.setattr(agent_service, "_apply_document_validation_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_reranking_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_subanswer_generation_to_sub_qa", passthrough)
    monkeypatch.setattr(agent_service, "_apply_subanswer_verification_to_sub_qa", fast_subanswer_verification)

    input_item = agent_service.SubQuestionAnswer(
        sub_question="What changed in NATO policy?",
        sub_answer="1. title=Doc A source=wiki://a content=A",
        tool_call_input='{"query":"What changed in NATO policy?"}',
    )

    output_item = agent_service._run_pipeline_for_single_subquestion(input_item)

    assert output_item.answerable is True
    assert output_item.verification_reason == "grounded_in_reranked_documents"


def test_seed_refined_sub_qa_from_retrieval_builds_retrieved_payloads(monkeypatch) -> None:
    class _Doc:
        def __init__(self, title: str, source: str, content: str):
            self.metadata = {"title": title, "source": source}
            self.page_content = content

    def fake_search_documents_for_context(*, vector_store, query, k, score_threshold):
        _ = vector_store, score_threshold
        return [_Doc(title=f"{query} Title", source="wiki://refined", content=f"Evidence for {query}")]

    monkeypatch.setattr(agent_service, "search_documents_for_context", fake_search_documents_for_context)
    monkeypatch.setattr(agent_service, "_REFINEMENT_RETRIEVAL_K", 3)
    monkeypatch.setattr(agent_service, "_SUBQUESTION_PIPELINE_MAX_WORKERS", 2)

    seeded = agent_service._seed_refined_sub_qa_from_retrieval(
        vector_store="fake-vector-store",
        refined_subquestions=["Refined Q1?", "Refined Q2?"],
    )

    assert len(seeded) == 2
    assert seeded[0].sub_question == "Refined Q1?"
    assert seeded[1].sub_question == "Refined Q2?"
    assert seeded[0].sub_answer.startswith("1. title=Refined Q1? Title source=wiki://refined")
    assert seeded[1].sub_answer.startswith("1. title=Refined Q2? Title source=wiki://refined")
    assert seeded[0].tool_call_input == '{"query": "Refined Q1?", "limit": 3}'
    assert seeded[1].tool_call_input == '{"query": "Refined Q2?", "limit": 3}'


def test_run_runtime_agent_populates_multiple_subquestions_with_verification(monkeypatch) -> None:
    class _FakeAgent:
        def invoke(self, payload, **kwargs):
            _ = payload, kwargs
            return {
                "messages": [
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_task_1",
                                "name": "task",
                                "args": {"description": "What changed in policy X?", "subagent_type": "rag_retriever"},
                            },
                            {
                                "id": "call_task_2",
                                "name": "task",
                                "args": {"description": "What changed in policy Y?", "subagent_type": "rag_retriever"},
                            },
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
                    ToolMessage(content="Policy X evidence.", tool_call_id="call_sd_1", name="search_database"),
                    AIMessage(content="Subagent completed policy X."),
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": "call_sd_2",
                                "name": "search_database",
                                "args": {"query": "What changed in policy Y?", "limit": 10},
                            }
                        ],
                    ),
                    ToolMessage(content="Policy Y evidence.", tool_call_id="call_sd_2", name="search_database"),
                    AIMessage(content="Subagent completed policy Y."),
                    AIMessage(content="Final output"),
                ]
            }

    monkeypatch.setattr(agent_service, "get_vector_store", lambda **kwargs: "fake-vector-store")
    monkeypatch.setattr(agent_service, "create_coordinator_agent", lambda **kwargs: _FakeAgent())
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", lambda **kwargs: [])
    monkeypatch.setattr(agent_service, "build_initial_search_context", lambda documents: [])
    monkeypatch.setattr(
        agent_service,
        "generate_initial_answer",
        lambda *, main_question, initial_search_context, sub_qa: "Initial synthesized output",
    )
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output: f"answer:{sub_question}",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )
    monkeypatch.setattr(agent_service, "_SUBQUESTION_PIPELINE_MAX_WORKERS", 2)

    response = agent_service.run_runtime_agent(
        RuntimeAgentRunRequest(query="What changed in policy X and Y?"),
        db=_make_session(),
    )

    assert response.output == "Initial synthesized output"
    assert len(response.sub_qa) == 2
    assert [item.sub_question for item in response.sub_qa] == [
        "What changed in policy X?",
        "What changed in policy Y?",
    ]
    assert [item.sub_answer for item in response.sub_qa] == [
        "answer:What changed in policy X?",
        "answer:What changed in policy Y?",
    ]
    assert all(item.answerable for item in response.sub_qa)
    assert all(item.verification_reason == "grounded_in_reranked_documents" for item in response.sub_qa)
