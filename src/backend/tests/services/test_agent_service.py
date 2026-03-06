import logging
import sys
import time
from pathlib import Path

from langchain_core.messages import AIMessage, ToolMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schemas import RuntimeAgentRunRequest
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

    monkeypatch.setattr(agent_service, "get_vector_store", fake_get_vector_store)
    monkeypatch.setattr(agent_service, "create_coordinator_agent", fake_create_coordinator_agent)
    monkeypatch.setattr(agent_service, "get_embedding_model", lambda: "fake-embeddings")
    monkeypatch.setattr(agent_service, "search_documents_for_context", fake_search_documents_for_context)
    monkeypatch.setattr(agent_service, "build_initial_search_context", fake_build_initial_search_context)
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
    assert captured["initial_answer_input"]["main_question"] == "What happened in NATO policy?"
    assert captured["initial_answer_input"]["sub_qa_count"] == 1
    assert captured["initial_answer_input"]["initial_search_context"][0]["title"] == "NATO"
    coordinator_message = captured["payload"]["messages"][0].content
    assert "Decomposition input:" in coordinator_message
    assert "User question:" in coordinator_message
    assert "What happened in NATO policy?" in coordinator_message
    assert "Initial retrieval context for decomposition" in coordinator_message
    assert '"title": "NATO"' in coordinator_message
    assert "Decomposition constraints:" in coordinator_message
    assert "One concept per sub-question." in coordinator_message
    assert "Every sub-question must be a complete question ending with '?'." in coordinator_message
    assert "Runtime agent run start" in caplog.text
    assert "Initial decomposition context built" in caplog.text
    assert "Coordinator decomposition input prepared" in caplog.text


def test_run_runtime_agent_flags_refinement_path_when_decision_true(monkeypatch, caplog) -> None:
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
    monkeypatch.setattr(agent_service, "generate_initial_answer", lambda **_: "Initial answer with gaps")
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

    with caplog.at_level(logging.INFO):
        response = agent_service.run_runtime_agent(
            RuntimeAgentRunRequest(query="What changed in policy?"),
            db=_make_session(),
        )

    assert response.output == "Initial answer with gaps"
    assert "Refinement decision computed refinement_needed=True reason=low_answerable_ratio:0.00" in caplog.text
    assert "Refinement path flagged but deferred until Section 13 implementation" in caplog.text
    assert "SubQuestionAnswer summary count=1" in caplog.text
    assert "SubQuestionAnswer[1]" in caplog.text and "What changed in policy?" in caplog.text
    assert "Coordinator raw output captured" in caplog.text
    assert "Runtime agent run complete" in caplog.text


def test_build_coordinator_input_message_includes_context_and_constraints_when_empty_context() -> None:
    message = agent_service._build_coordinator_input_message("Explain VAT changes", [])

    assert "User question:\nExplain VAT changes" in message
    assert "Initial retrieval context for decomposition" in message
    assert "[]" in message
    assert "Decomposition constraints:" in message
    assert "Every sub-question must be a complete question ending with '?'." in message


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
