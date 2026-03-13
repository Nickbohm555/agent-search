import logging
import json
import sys
import time
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schemas import (
    AnswerSubquestionNodeInput,
    AnswerSubquestionNodeOutput,
    CitationSourceRow,
    DecomposeNodeInput,
    ExpandNodeInput,
    ExpandNodeOutput,
    RerankNodeInput,
    RerankNodeOutput,
    RuntimeAgentRunRequest,
    SearchNodeInput,
    SearchNodeOutput,
    SynthesizeFinalNodeInput,
    SynthesizeFinalNodeOutput,
)
from agent_search.runtime.graph.builder import build_runtime_graph
from agent_search.runtime.graph.execution import execute_runtime_graph
from agent_search.runtime.graph.routes import route_post_decompose
from agent_search.runtime.graph.state import RuntimeGraphContext, to_runtime_graph_state
from schemas.decomposition import DecompositionPlan
from agent_search.runtime import runner as runtime_runner
from models import RuntimeExecutionRun, RuntimeIdempotencyEffect
from services import agent_jobs
from services import document_validation_service
from services import agent_service
from services import idempotency_service
from services import reranker_service


def _make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    return Session(engine)


def _make_runtime_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    RuntimeExecutionRun.__table__.create(engine)
    RuntimeIdempotencyEffect.__table__.create(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _serialize_agent_graph_state(state: agent_service.AgentGraphState) -> dict[str, object]:
    return state.model_dump(mode="json")


def test_build_runtime_timeout_config_from_env_defaults(monkeypatch) -> None:
    keys = [
        "VECTOR_STORE_ACQUISITION_TIMEOUT_S",
        "INITIAL_SEARCH_TIMEOUT_S",
        "DECOMPOSITION_LLM_TIMEOUT_S",
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
    assert config.document_validation_timeout_s == 20
    assert config.rerank_timeout_s == 1
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
    assert len(response.sub_answers) == 1
    assert response.sub_answers[0].model_dump() == response.sub_qa[0].model_dump()

    response.sub_answers[0].sub_answer = "mutated alias copy"

    assert response.sub_qa[0].sub_answer == "sub-answer"
    assert response.sub_answers[0].sub_answer == "mutated alias copy"


def test_build_runtime_graph_compiles_into_callable_graph() -> None:
    graph = build_runtime_graph(
        context=RuntimeGraphContext(
            payload=RuntimeAgentRunRequest(query="Main question?"),
        )
    )

    assert callable(graph.invoke)
    assert {"decompose", "expand", "search", "rerank", "answer", "synthesize"} <= set(graph.get_graph().nodes)


def test_route_post_decompose_fans_out_one_expand_send_per_subquestion() -> None:
    run_metadata = agent_service.build_graph_run_metadata(run_id="run-route")
    state = to_runtime_graph_state(
        RuntimeAgentRunRequest(query="Main question?"),
        run_metadata=run_metadata,
        initial_search_context=[{"rank": 1, "title": "Initial context"}],
    )
    state["decomposition_sub_questions"] = ["Sub-question A?", "Sub-question B?"]

    routed = route_post_decompose(state)

    assert [send.node for send in routed] == ["lane_pipeline", "lane_pipeline"]
    assert [send.arg["decomposition_sub_questions"] for send in routed] == [
        ["Sub-question A?", "Sub-question B?"],
        ["Sub-question A?", "Sub-question B?"],
    ]
    assert [send.arg["lane_sub_question"] for send in routed] == ["Sub-question A?", "Sub-question B?"]
    assert all(send.arg["main_question"] == "Main question?" for send in routed)
    assert all(send.arg["run_metadata"].run_id == "run-route" for send in routed)
    assert all(send.arg["sub_question_artifacts"] == [] for send in routed)
    assert all(send.arg["sub_qa"] == [] for send in routed)
    assert all(send.arg["citation_rows_by_index"] == {} for send in routed)


def test_execute_runtime_graph_preserves_deterministic_fan_in_order(monkeypatch) -> None:
    def fake_run_decomposition_node(*, node_input, model=None, timeout_s=None, callbacks=None):
        _ = node_input, model, timeout_s, callbacks
        return agent_service.DecomposeNodeOutput(
            decomposition_sub_questions=["Sub-question A?", "Sub-question B?"]
        )

    def fake_run_expand_node(*, node_input, model=None, config=None, callbacks=None):
        _ = model, config, callbacks
        if node_input.sub_question == "Sub-question A?":
            time.sleep(0.05)
        return agent_service.ExpandNodeOutput(
            expanded_queries=[node_input.sub_question, f"{node_input.sub_question} alt"]
        )

    def fake_run_search_node(*, node_input, vector_store, k_fetch=None):
        _ = vector_store, k_fetch
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Doc for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Evidence for {node_input.sub_question}",
            document_id=f"doc-{node_input.sub_question}",
        )
        return agent_service.SearchNodeOutput(
            retrieved_docs=[row],
            retrieval_provenance=[{"query": node_input.sub_question, "deduped": False}],
            citation_rows_by_index={1: row},
        )

    def fake_run_rerank_node(*, node_input, config=None, callbacks=None):
        _ = config, callbacks
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Reranked for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Reranked evidence for {node_input.sub_question}",
            document_id=f"reranked-{node_input.sub_question}",
            score=0.8,
        )
        return agent_service.RerankNodeOutput(
            reranked_docs=[row],
            citation_rows_by_index={1: row},
        )

    def fake_run_answer_subquestion_node(*, node_input, callbacks=None):
        _ = callbacks
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Answer source for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Answer evidence for {node_input.sub_question}",
            document_id=f"answer-{node_input.sub_question}",
            score=0.8,
        )
        return agent_service.AnswerSubquestionNodeOutput(
            sub_answer=f"Answer for {node_input.sub_question} [1].",
            citation_indices_used=[1],
            answerable=True,
            verification_reason="grounded_in_reranked_documents",
            citation_rows_by_index={1: row},
        )

    def fake_run_synthesize_final_node(*, node_input, callbacks=None):
        _ = callbacks
        return agent_service.SynthesizeFinalNodeOutput(
            final_answer=" | ".join(item.sub_question for item in node_input.sub_qa)
        )

    monkeypatch.setattr(agent_service, "run_decomposition_node", fake_run_decomposition_node)
    monkeypatch.setattr(agent_service, "run_expand_node", fake_run_expand_node)
    monkeypatch.setattr(agent_service, "run_search_node", fake_run_search_node)
    monkeypatch.setattr(agent_service, "run_rerank_node", fake_run_rerank_node)
    monkeypatch.setattr(agent_service, "run_answer_subquestion_node", fake_run_answer_subquestion_node)
    monkeypatch.setattr(agent_service, "run_synthesize_final_node", fake_run_synthesize_final_node)

    results = [
        execute_runtime_graph(
            context=RuntimeGraphContext(
                payload=RuntimeAgentRunRequest(query="Main question?"),
                model="fake-model",
                vector_store="fake-store",
                initial_search_context=[{"rank": 1, "title": "Initial context"}],
            ),
            run_metadata=agent_service.build_graph_run_metadata(run_id=f"run-langgraph-{index}"),
        )
        for index in range(3)
    ]

    assert [
        [item.sub_question for item in result["sub_qa"]]
        for result in results
    ] == [["Sub-question A?", "Sub-question B?"]] * 3
    assert [
        [item.sub_question for item in result["sub_question_artifacts"]]
        for result in results
    ] == [["Sub-question A?", "Sub-question B?"]] * 3
    assert [result["output"] for result in results] == [
        "Sub-question A? | Sub-question B?"
    ] * 3


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


def test_apply_decompose_node_output_to_graph_state_initializes_artifacts_and_compat_fields() -> None:
    state = agent_service.build_agent_graph_state(
        main_question="Explain VAT changes.",
        decomposition_sub_questions=[],
        sub_qa=[],
        final_answer="",
        run_metadata=agent_service.build_graph_run_metadata(run_id="run-decompose-state"),
    )

    updated = agent_service.apply_decompose_node_output_to_graph_state(
        state=state,
        node_output=agent_service.DecomposeNodeOutput(
            decomposition_sub_questions=[
                "What changed in VAT policy?",
                "Why did VAT policy change?",
            ]
        ),
    )

    assert updated.decomposition_sub_questions == [
        "What changed in VAT policy?",
        "Why did VAT policy change?",
    ]
    assert [item.sub_question for item in updated.sub_question_artifacts] == [
        "What changed in VAT policy?",
        "Why did VAT policy change?",
    ]
    assert [item.sub_question for item in updated.sub_qa] == [
        "What changed in VAT policy?",
        "Why did VAT policy change?",
    ]
    assert all(item.sub_answer == "" for item in updated.sub_qa)


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


def test_run_search_node_merges_and_dedupes_multi_query_results(monkeypatch) -> None:
    class _Doc:
        def __init__(self, *, doc_id: str, title: str, source: str, content: str):
            self.id = doc_id
            self.metadata = {"title": title, "source": source}
            self.page_content = content

    def fake_search_documents_for_queries(*, vector_store, queries, k, score_threshold):
        assert queries == [
            "What changed in VAT policy?",
            "VAT policy updates 2025",
            "VAT changes by region",
        ]
        assert k == 7
        return {
            "What changed in VAT policy?": [
                _Doc(doc_id="doc-1", title="Policy Doc", source="wiki://policy", content="Policy changed in 2025."),
                _Doc(doc_id="", title="Regional Memo", source="wiki://memo", content="Regional changes by country."),
            ],
            "VAT policy updates 2025": [
                _Doc(doc_id="doc-1", title="Policy Doc Duplicate", source="wiki://policy", content="Duplicate by id."),
                _Doc(
                    doc_id="",
                    title="Regional Memo Duplicate",
                    source="wiki://memo",
                    content="Regional changes by country.",
                ),
                _Doc(doc_id="doc-4", title="Timeline", source="wiki://timeline", content="Timeline details."),
            ],
            "VAT changes by region": [
                _Doc(doc_id="doc-5", title="Region Breakdown", source="wiki://regions", content="Region-by-region notes.")
            ],
        }

    monkeypatch.setattr(agent_service, "search_documents_for_queries", fake_search_documents_for_queries)

    output = agent_service.run_search_node(
        node_input=SearchNodeInput(
            sub_question="What changed in VAT policy?",
            expanded_queries=["VAT policy updates 2025", "VAT changes by region"],
            run_metadata=agent_service.build_graph_run_metadata(run_id="run-search-node"),
        ),
        vector_store="fake-store",
        k_fetch=7,
    )

    assert [item.document_id for item in output.retrieved_docs] == ["doc-1", "", "doc-4", "doc-5"]
    assert [item.rank for item in output.retrieved_docs] == [1, 2, 3, 4]
    assert [item.citation_index for item in output.retrieved_docs] == [1, 2, 3, 4]
    assert len(output.retrieval_provenance) == 6
    assert sum(1 for item in output.retrieval_provenance if item["deduped"]) == 2
    assert output.citation_rows_by_index[1].title == "Policy Doc"
    assert output.citation_rows_by_index[3].title == "Timeline"


def test_apply_search_node_output_to_graph_state_updates_artifacts_and_compat_fields() -> None:
    state = agent_service.build_agent_graph_state(
        main_question="Explain VAT changes",
        decomposition_sub_questions=["What changed in VAT policy?"],
        sub_qa=[
            agent_service.SubQuestionAnswer(
                sub_question="What changed in VAT policy?",
                sub_answer="",
                expanded_query="VAT policy updates 2025",
            )
        ],
        run_metadata=agent_service.build_graph_run_metadata(run_id="run-search-state"),
    )
    state = agent_service.apply_expand_node_output_to_graph_state(
        state=state,
        sub_question="What changed in VAT policy?",
        node_output=ExpandNodeOutput(
            expanded_queries=["What changed in VAT policy?", "VAT policy updates 2025"]
        ),
    )
    node_output = SearchNodeOutput(
        retrieved_docs=[
            agent_service.CitationSourceRow(
                citation_index=1,
                rank=1,
                title="VAT Policy",
                source="wiki://vat-policy",
                content="VAT policy changed in 2025.",
                document_id="doc-1",
            ),
            agent_service.CitationSourceRow(
                citation_index=2,
                rank=2,
                title="VAT Timeline",
                source="wiki://vat-timeline",
                content="Timeline details for VAT changes.",
                document_id="doc-2",
            ),
        ],
        retrieval_provenance=[
            {
                "query": "What changed in VAT policy?",
                "query_index": 1,
                "query_rank": 1,
                "document_identity": "document_id:doc-1",
                "deduped": False,
            },
            {
                "query": "VAT policy updates 2025",
                "query_index": 2,
                "query_rank": 1,
                "document_identity": "document_id:doc-2",
                "deduped": False,
            },
        ],
        citation_rows_by_index={
            1: agent_service.CitationSourceRow(
                citation_index=1,
                rank=1,
                title="VAT Policy",
                source="wiki://vat-policy",
                content="VAT policy changed in 2025.",
                document_id="doc-1",
            ),
            2: agent_service.CitationSourceRow(
                citation_index=2,
                rank=2,
                title="VAT Timeline",
                source="wiki://vat-timeline",
                content="Timeline details for VAT changes.",
                document_id="doc-2",
            ),
        },
    )

    updated = agent_service.apply_search_node_output_to_graph_state(
        state=state,
        sub_question="What changed in VAT policy?",
        node_output=node_output,
    )

    assert len(updated.sub_question_artifacts[0].retrieved_docs) == 2
    assert len(updated.sub_question_artifacts[0].retrieval_provenance) == 2
    assert updated.citation_rows_by_index[1].source == "wiki://vat-policy"
    assert updated.sub_qa[0].sub_answer.startswith("1. title=VAT Policy")
    tool_call_input = json.loads(updated.sub_qa[0].tool_call_input)
    assert tool_call_input["query"] == "What changed in VAT policy?"
    assert len(tool_call_input["retrieval_provenance"]) == 2


def test_run_rerank_node_reorders_and_trims_documents(monkeypatch) -> None:
    def fake_rerank_documents(*, query, documents, config, callbacks=None):
        assert query == "What changed in VAT policy?"
        assert len(documents) == 3
        return [
            reranker_service.RerankedDocumentScore(
                document=document_validation_service.RetrievedDocument(
                    rank=1,
                    title="VAT Timeline",
                    source="wiki://vat-timeline",
                    content="Timeline details for VAT changes.",
                ),
                score=0.88,
                original_rank=2,
                reranked_rank=1,
            ),
            reranker_service.RerankedDocumentScore(
                document=document_validation_service.RetrievedDocument(
                    rank=2,
                    title="VAT Policy",
                    source="wiki://vat-policy",
                    content="VAT policy changed in 2025.",
                ),
                score=0.63,
                original_rank=1,
                reranked_rank=2,
            ),
        ]

    monkeypatch.setattr(agent_service, "rerank_documents", fake_rerank_documents)

    output = agent_service.run_rerank_node(
        node_input=RerankNodeInput(
            sub_question="What changed in VAT policy?",
            retrieved_docs=[
                agent_service.CitationSourceRow(
                    citation_index=1,
                    rank=1,
                    title="VAT Policy",
                    source="wiki://vat-policy",
                    content="VAT policy changed in 2025.",
                    document_id="doc-1",
                ),
                agent_service.CitationSourceRow(
                    citation_index=2,
                    rank=2,
                    title="VAT Timeline",
                    source="wiki://vat-timeline",
                    content="Timeline details for VAT changes.",
                    document_id="doc-2",
                ),
                agent_service.CitationSourceRow(
                    citation_index=3,
                    rank=3,
                    title="VAT FAQ",
                    source="wiki://vat-faq",
                    content="Frequently asked questions.",
                    document_id="doc-3",
                ),
            ],
            run_metadata=agent_service.build_graph_run_metadata(run_id="run-rerank-node"),
        ),
    )

    assert [item.title for item in output.reranked_docs] == ["VAT Timeline", "VAT Policy"]
    assert [item.document_id for item in output.reranked_docs] == ["doc-2", "doc-1"]
    assert [item.score for item in output.reranked_docs] == [0.88, 0.63]
    assert output.citation_rows_by_index[1].title == "VAT Timeline"


def test_apply_rerank_node_output_to_graph_state_updates_artifacts_and_compat_fields() -> None:
    state = agent_service.build_agent_graph_state(
        main_question="Explain VAT changes",
        decomposition_sub_questions=["What changed in VAT policy?"],
        sub_qa=[
            agent_service.SubQuestionAnswer(
                sub_question="What changed in VAT policy?",
                sub_answer="1. title=VAT Policy source=wiki://vat-policy content=VAT policy changed in 2025.",
                tool_call_input=json.dumps(
                    {
                        "query": "What changed in VAT policy?",
                        "expanded_queries": ["What changed in VAT policy?", "VAT policy updates 2025"],
                    }
                ),
                expanded_query="VAT policy updates 2025",
            )
        ],
        run_metadata=agent_service.build_graph_run_metadata(run_id="run-rerank-state"),
    )
    node_output = RerankNodeOutput(
        reranked_docs=[
            agent_service.CitationSourceRow(
                citation_index=1,
                rank=1,
                title="VAT Timeline",
                source="wiki://vat-timeline",
                content="Timeline details for VAT changes.",
                document_id="doc-2",
                score=0.88,
            ),
            agent_service.CitationSourceRow(
                citation_index=2,
                rank=2,
                title="VAT Policy",
                source="wiki://vat-policy",
                content="VAT policy changed in 2025.",
                document_id="doc-1",
                score=0.63,
            ),
        ],
        citation_rows_by_index={
            1: agent_service.CitationSourceRow(
                citation_index=1,
                rank=1,
                title="VAT Timeline",
                source="wiki://vat-timeline",
                content="Timeline details for VAT changes.",
                document_id="doc-2",
                score=0.88,
            ),
            2: agent_service.CitationSourceRow(
                citation_index=2,
                rank=2,
                title="VAT Policy",
                source="wiki://vat-policy",
                content="VAT policy changed in 2025.",
                document_id="doc-1",
                score=0.63,
            ),
        },
    )

    updated = agent_service.apply_rerank_node_output_to_graph_state(
        state=state,
        sub_question="What changed in VAT policy?",
        node_output=node_output,
    )

    assert len(updated.sub_question_artifacts[0].reranked_docs) == 2
    assert updated.sub_question_artifacts[0].reranked_docs[0].title == "VAT Timeline"
    assert updated.sub_qa[0].sub_answer.startswith("1. title=VAT Timeline")
    tool_call_input = json.loads(updated.sub_qa[0].tool_call_input)
    assert tool_call_input["query"] == "What changed in VAT policy?"
    assert len(tool_call_input["rerank_provenance"]) == 2
    assert tool_call_input["rerank_provenance"][0]["score"] == 0.88


def test_run_answer_subquestion_node_returns_cited_grounded_answer(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output, callbacks=None: "VAT changes were enacted in 2025 [2].",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )

    output = agent_service.run_answer_subquestion_node(
        node_input=AnswerSubquestionNodeInput(
            sub_question="What changed in VAT policy?",
            reranked_docs=[
                agent_service.CitationSourceRow(
                    citation_index=1,
                    rank=1,
                    title="VAT Policy",
                    source="wiki://vat-policy",
                    content="VAT policy changed in 2025.",
                    document_id="doc-1",
                ),
                agent_service.CitationSourceRow(
                    citation_index=2,
                    rank=2,
                    title="VAT Timeline",
                    source="wiki://vat-timeline",
                    content="Timeline details for VAT changes.",
                    document_id="doc-2",
                ),
            ],
            citation_rows_by_index={
                1: agent_service.CitationSourceRow(
                    citation_index=1,
                    rank=1,
                    title="VAT Policy",
                    source="wiki://vat-policy",
                    content="VAT policy changed in 2025.",
                    document_id="doc-1",
                ),
                2: agent_service.CitationSourceRow(
                    citation_index=2,
                    rank=2,
                    title="VAT Timeline",
                    source="wiki://vat-timeline",
                    content="Timeline details for VAT changes.",
                    document_id="doc-2",
                ),
            },
            run_metadata=agent_service.build_graph_run_metadata(run_id="run-answer-node"),
        ),
    )

    assert output.sub_answer == "VAT changes were enacted in 2025 [2]."
    assert output.citation_indices_used == [2]
    assert output.answerable is True
    assert output.verification_reason == "grounded_in_reranked_documents"
    assert list(output.citation_rows_by_index.keys()) == [2]
    assert output.citation_rows_by_index[2].title == "VAT Timeline"


def test_run_answer_subquestion_node_falls_back_when_answer_is_not_supported(monkeypatch) -> None:
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output, callbacks=None: "This changed in ways we cannot verify.",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=False,
            reason="insufficient_evidence_overlap",
        ),
    )

    output = agent_service.run_answer_subquestion_node(
        node_input=AnswerSubquestionNodeInput(
            sub_question="What changed in VAT policy?",
            reranked_docs=[
                agent_service.CitationSourceRow(
                    citation_index=1,
                    rank=1,
                    title="VAT Policy",
                    source="wiki://vat-policy",
                    content="VAT policy changed in 2025.",
                    document_id="doc-1",
                ),
            ],
            citation_rows_by_index={
                1: agent_service.CitationSourceRow(
                    citation_index=1,
                    rank=1,
                    title="VAT Policy",
                    source="wiki://vat-policy",
                    content="VAT policy changed in 2025.",
                    document_id="doc-1",
                ),
            },
            run_metadata=agent_service.build_graph_run_metadata(run_id="run-answer-node-fallback"),
        ),
    )

    assert output.sub_answer == "nothing relevant found"
    assert output.citation_indices_used == []
    assert output.answerable is False
    assert output.verification_reason == "insufficient_evidence_overlap"
    assert output.citation_rows_by_index == {}


def test_apply_answer_subquestion_node_output_to_graph_state_updates_artifacts_and_compat_fields() -> None:
    state = agent_service.build_agent_graph_state(
        main_question="Explain VAT changes",
        decomposition_sub_questions=["What changed in VAT policy?"],
        sub_qa=[
            agent_service.SubQuestionAnswer(
                sub_question="What changed in VAT policy?",
                sub_answer="",
                tool_call_input=json.dumps({"query": "What changed in VAT policy?"}),
            )
        ],
        run_metadata=agent_service.build_graph_run_metadata(run_id="run-answer-state"),
    )

    updated = agent_service.apply_answer_subquestion_node_output_to_graph_state(
        state=state,
        sub_question="What changed in VAT policy?",
        node_output=AnswerSubquestionNodeOutput(
            sub_answer="VAT changes were enacted in 2025 [1].",
            citation_indices_used=[1],
            answerable=True,
            verification_reason="grounded_in_reranked_documents",
            citation_rows_by_index={
                1: agent_service.CitationSourceRow(
                    citation_index=1,
                    rank=1,
                    title="VAT Policy",
                    source="wiki://vat-policy",
                    content="VAT policy changed in 2025.",
                    document_id="doc-1",
                    score=0.77,
                )
            },
        ),
    )

    assert updated.sub_question_artifacts[0].sub_answer == "VAT changes were enacted in 2025 [1]."
    assert updated.sub_question_artifacts[0].citation_rows_by_index[1].source == "wiki://vat-policy"
    assert updated.sub_qa[0].sub_answer == "VAT changes were enacted in 2025 [1]."
    assert updated.sub_qa[0].answerable is True
    assert updated.sub_qa[0].verification_reason == "grounded_in_reranked_documents"
    tool_call_input = json.loads(updated.sub_qa[0].tool_call_input)
    assert tool_call_input["query"] == "What changed in VAT policy?"
    assert tool_call_input["citation_usage"] == [1]
    assert tool_call_input["supporting_source_rows"][0]["source"] == "wiki://vat-policy"


def test_run_synthesize_final_node_uses_subanswers_as_grounded_inputs(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_generate_final_synthesis_answer(*, main_question: str, sub_qa, callbacks=None):
        captured["main_question"] = main_question
        captured["sub_qa_count"] = len(sub_qa)
        return "Final synthesis [1] (source: wiki://vat-policy)."

    monkeypatch.setattr(agent_service, "generate_final_synthesis_answer", fake_generate_final_synthesis_answer)

    output = agent_service.run_synthesize_final_node(
        node_input=SynthesizeFinalNodeInput(
            main_question="Explain VAT policy changes.",
            sub_qa=[
                agent_service.SubQuestionAnswer(
                    sub_question="What changed in VAT policy?",
                    sub_answer="VAT changed in 2025 [1] (source: wiki://vat-policy).",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                )
            ],
            sub_question_artifacts=[
                agent_service.SubQuestionArtifacts(
                    sub_question="What changed in VAT policy?",
                    sub_answer="VAT changed in 2025 [1] (source: wiki://vat-policy).",
                )
            ],
            run_metadata=agent_service.build_graph_run_metadata(run_id="run-synthesize-node"),
        ),
    )

    assert output.final_answer == "Final synthesis [1] (source: wiki://vat-policy)."
    assert captured["main_question"] == "Explain VAT policy changes."
    assert captured["sub_qa_count"] == 1


def test_run_synthesize_final_node_falls_back_when_final_answer_has_no_citations(monkeypatch) -> None:
    def fake_generate_final_synthesis_answer(*, main_question: str, sub_qa, callbacks=None):
        _ = main_question, sub_qa
        return "VAT policy changed in 2025."

    monkeypatch.setattr(agent_service, "generate_final_synthesis_answer", fake_generate_final_synthesis_answer)

    output = agent_service.run_synthesize_final_node(
        node_input=SynthesizeFinalNodeInput(
            main_question="Explain VAT policy changes.",
            sub_qa=[
                agent_service.SubQuestionAnswer(
                    sub_question="What changed in VAT policy?",
                    sub_answer="VAT changed in 2025 [1] (source: wiki://vat-policy).",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                )
            ],
            sub_question_artifacts=[
                agent_service.SubQuestionArtifacts(
                    sub_question="What changed in VAT policy?",
                    sub_answer="VAT changed in 2025 [1] (source: wiki://vat-policy).",
                    citation_rows_by_index={
                        1: agent_service.CitationSourceRow(
                            citation_index=1,
                            rank=1,
                            title="VAT Policy",
                            source="wiki://vat-policy",
                            content="VAT policy changed in 2025.",
                            document_id="doc-1",
                        )
                    },
                )
            ],
            run_metadata=agent_service.build_graph_run_metadata(run_id="run-synthesize-citation-fallback"),
        ),
    )

    assert output.final_answer == "VAT changed in 2025 [1] (source: wiki://vat-policy)."


def test_run_synthesize_final_node_falls_back_when_final_answer_uses_invalid_citations(monkeypatch) -> None:
    def fake_generate_final_synthesis_answer(*, main_question: str, sub_qa, callbacks=None):
        _ = main_question, sub_qa
        return "VAT policy changed in 2025 [9] (source: wiki://vat-policy)."

    monkeypatch.setattr(agent_service, "generate_final_synthesis_answer", fake_generate_final_synthesis_answer)

    output = agent_service.run_synthesize_final_node(
        node_input=SynthesizeFinalNodeInput(
            main_question="Explain VAT policy changes.",
            sub_qa=[
                agent_service.SubQuestionAnswer(
                    sub_question="What changed in VAT policy?",
                    sub_answer="VAT changed in 2025 [1] (source: wiki://vat-policy).",
                    answerable=True,
                    verification_reason="grounded_in_reranked_documents",
                )
            ],
            sub_question_artifacts=[
                agent_service.SubQuestionArtifacts(
                    sub_question="What changed in VAT policy?",
                    sub_answer="VAT changed in 2025 [1] (source: wiki://vat-policy).",
                    citation_rows_by_index={
                        1: agent_service.CitationSourceRow(
                            citation_index=1,
                            rank=1,
                            title="VAT Policy",
                            source="wiki://vat-policy",
                            content="VAT policy changed in 2025.",
                            document_id="doc-1",
                        )
                    },
                )
            ],
            run_metadata=agent_service.build_graph_run_metadata(run_id="run-synthesize-invalid-citation"),
        ),
    )

    assert output.final_answer == "VAT changed in 2025 [1] (source: wiki://vat-policy)."


def test_apply_synthesize_final_node_output_to_graph_state_updates_final_answer_and_output() -> None:
    state = agent_service.build_agent_graph_state(
        main_question="Explain VAT policy changes.",
        decomposition_sub_questions=["What changed in VAT policy?"],
        sub_qa=[
            agent_service.SubQuestionAnswer(
                sub_question="What changed in VAT policy?",
                sub_answer="VAT changed in 2025 [1] (source: wiki://vat-policy).",
                answerable=True,
                verification_reason="grounded_in_reranked_documents",
            )
        ],
        final_answer="Old answer",
        run_metadata=agent_service.build_graph_run_metadata(run_id="run-synthesize-state"),
    )

    updated = agent_service.apply_synthesize_final_node_output_to_graph_state(
        state=state,
        node_output=SynthesizeFinalNodeOutput(
            final_answer="Final synthesis [1] (source: wiki://vat-policy).",
        ),
    )

    assert updated.final_answer == "Final synthesis [1] (source: wiki://vat-policy)."
    assert updated.output == "Final synthesis [1] (source: wiki://vat-policy)."
    assert len(updated.sub_qa) == 1


def test_run_sequential_graph_runner_executes_strict_node_order(monkeypatch) -> None:
    call_order: list[str] = []
    captured_flush: dict[str, object] = {}

    def fake_run_decomposition_node(*, node_input, model=None, timeout_s=None, callbacks=None):
        _ = model, timeout_s
        call_order.append("decompose")
        return agent_service.DecomposeNodeOutput(
            decomposition_sub_questions=["Sub-question A?", "Sub-question B?"]
        )

    def fake_run_expand_node(*, node_input, model=None, config=None, callbacks=None):
        _ = model, config
        call_order.append(f"expand:{node_input.sub_question}")
        return agent_service.ExpandNodeOutput(
            expanded_queries=[node_input.sub_question, f"{node_input.sub_question} alt"]
        )

    def fake_run_search_node(*, node_input, vector_store, k_fetch=None):
        _ = vector_store, k_fetch
        call_order.append(f"search:{node_input.sub_question}")
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Doc for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Evidence for {node_input.sub_question}",
            document_id=f"doc-{node_input.sub_question}",
        )
        return agent_service.SearchNodeOutput(
            retrieved_docs=[row],
            retrieval_provenance=[{"query": node_input.sub_question, "deduped": False}],
            citation_rows_by_index={1: row},
        )

    def fake_run_rerank_node(*, node_input, config=None, callbacks=None):
        _ = config
        call_order.append(f"rerank:{node_input.sub_question}")
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Reranked for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Reranked evidence for {node_input.sub_question}",
            document_id=f"reranked-{node_input.sub_question}",
            score=0.8,
        )
        return agent_service.RerankNodeOutput(
            reranked_docs=[row],
            citation_rows_by_index={1: row},
        )

    def fake_run_answer_subquestion_node(*, node_input, callbacks=None):
        call_order.append(f"answer:{node_input.sub_question}")
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Answer source for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Answer evidence for {node_input.sub_question}",
            document_id=f"answer-{node_input.sub_question}",
            score=0.8,
        )
        return agent_service.AnswerSubquestionNodeOutput(
            sub_answer=f"Answer for {node_input.sub_question} [1].",
            citation_indices_used=[1],
            answerable=True,
            verification_reason="grounded_in_reranked_documents",
            citation_rows_by_index={1: row},
        )

    def fake_run_synthesize_final_node(*, node_input, callbacks=None):
        call_order.append("synthesize_final")
        return agent_service.SynthesizeFinalNodeOutput(
            final_answer=f"Final from {len(node_input.sub_qa)} subanswers."
        )

    class _FakeLangfuseCallback:
        pass

    langfuse_callback = _FakeLangfuseCallback()

    monkeypatch.setattr(agent_service, "run_decomposition_node", fake_run_decomposition_node)
    monkeypatch.setattr(agent_service, "run_expand_node", fake_run_expand_node)
    monkeypatch.setattr(agent_service, "run_search_node", fake_run_search_node)
    monkeypatch.setattr(agent_service, "run_rerank_node", fake_run_rerank_node)
    monkeypatch.setattr(agent_service, "run_answer_subquestion_node", fake_run_answer_subquestion_node)
    monkeypatch.setattr(agent_service, "run_synthesize_final_node", fake_run_synthesize_final_node)
    monkeypatch.setattr(
        agent_service,
        "flush_langfuse_callback_handler",
        lambda handler: captured_flush.__setitem__("handler", handler),
    )

    state = agent_service.run_sequential_graph_runner(
        payload=RuntimeAgentRunRequest(query="Main question?"),
        vector_store="fake-store",
        initial_search_context=[{"rank": 1, "title": "Initial context"}],
        run_metadata=agent_service.build_graph_run_metadata(run_id="run-seq"),
        langfuse_callback=langfuse_callback,
    )

    assert call_order == [
        "decompose",
        "expand:Sub-question A?",
        "search:Sub-question A?",
        "rerank:Sub-question A?",
        "answer:Sub-question A?",
        "expand:Sub-question B?",
        "search:Sub-question B?",
        "rerank:Sub-question B?",
        "answer:Sub-question B?",
        "synthesize_final",
    ]
    assert [item.sub_question for item in state.sub_qa] == ["Sub-question A?", "Sub-question B?"]
    assert state.output == "Final from 2 subanswers."
    assert captured_flush == {}


def test_run_parallel_graph_runner_preserves_subquestion_order_and_emits_snapshots(monkeypatch) -> None:
    completion_order: list[str] = []
    captured_flush: dict[str, object] = {}

    def fake_run_decomposition_node(*, node_input, model=None, timeout_s=None, callbacks=None):
        _ = node_input, model, timeout_s
        return agent_service.DecomposeNodeOutput(
            decomposition_sub_questions=["Sub-question A?", "Sub-question B?"]
        )

    def fake_run_expand_node(*, node_input, model=None, config=None, callbacks=None):
        _ = model, config
        if node_input.sub_question == "Sub-question A?":
            time.sleep(0.05)
        return agent_service.ExpandNodeOutput(
            expanded_queries=[node_input.sub_question, f"{node_input.sub_question} alt"]
        )

    def fake_run_search_node(*, node_input, vector_store, k_fetch=None):
        _ = vector_store, k_fetch
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Doc for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Evidence for {node_input.sub_question}",
            document_id=f"doc-{node_input.sub_question}",
        )
        return agent_service.SearchNodeOutput(
            retrieved_docs=[row],
            retrieval_provenance=[{"query": node_input.sub_question, "deduped": False}],
            citation_rows_by_index={1: row},
        )

    def fake_run_rerank_node(*, node_input, config=None, callbacks=None):
        _ = config
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Reranked for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Reranked evidence for {node_input.sub_question}",
            document_id=f"reranked-{node_input.sub_question}",
            score=0.8,
        )
        return agent_service.RerankNodeOutput(
            reranked_docs=[row],
            citation_rows_by_index={1: row},
        )

    def fake_run_answer_subquestion_node(*, node_input, callbacks=None):
        completion_order.append(node_input.sub_question)
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Answer source for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Answer evidence for {node_input.sub_question}",
            document_id=f"answer-{node_input.sub_question}",
            score=0.8,
        )
        return agent_service.AnswerSubquestionNodeOutput(
            sub_answer=f"Answer for {node_input.sub_question} [1].",
            citation_indices_used=[1],
            answerable=True,
            verification_reason="grounded_in_reranked_documents",
            citation_rows_by_index={1: row},
        )

    def fake_run_synthesize_final_node(*, node_input, callbacks=None):
        return agent_service.SynthesizeFinalNodeOutput(
            final_answer=f"Final from {len(node_input.sub_qa)} subanswers."
        )

    class _FakeLangfuseCallback:
        pass

    langfuse_callback = _FakeLangfuseCallback()

    monkeypatch.setattr(agent_service, "run_decomposition_node", fake_run_decomposition_node)
    monkeypatch.setattr(agent_service, "run_expand_node", fake_run_expand_node)
    monkeypatch.setattr(agent_service, "run_search_node", fake_run_search_node)
    monkeypatch.setattr(agent_service, "run_rerank_node", fake_run_rerank_node)
    monkeypatch.setattr(agent_service, "run_answer_subquestion_node", fake_run_answer_subquestion_node)
    monkeypatch.setattr(agent_service, "run_synthesize_final_node", fake_run_synthesize_final_node)
    monkeypatch.setattr(
        agent_service,
        "flush_langfuse_callback_handler",
        lambda handler: captured_flush.__setitem__("handler", handler),
    )

    state = agent_service.run_parallel_graph_runner(
        payload=RuntimeAgentRunRequest(query="Main question?"),
        vector_store="fake-store",
        initial_search_context=[{"rank": 1, "title": "Initial context"}],
        run_metadata=agent_service.build_graph_run_metadata(run_id="run-parallel"),
        langfuse_callback=langfuse_callback,
    )

    assert completion_order == ["Sub-question B?", "Sub-question A?"]
    assert [item.sub_question for item in state.sub_qa] == ["Sub-question A?", "Sub-question B?"]
    assert [item.sub_answer for item in state.sub_qa] == [
        "Answer for Sub-question A? [1].",
        "Answer for Sub-question B? [1].",
    ]
    assert state.output == "Final from 2 subanswers."
    assert [snapshot.stage for snapshot in state.stage_snapshots] == [
        "decompose",
        "expand",
        "search",
        "rerank",
        "answer",
        "expand",
        "search",
        "rerank",
        "answer",
        "synthesize_final",
    ]
    assert state.stage_snapshots[0].decomposition_sub_questions == ["Sub-question A?", "Sub-question B?"]
    assert state.stage_snapshots[0].lane_index == 0
    assert state.stage_snapshots[1].sub_question == "Sub-question A?"
    assert state.stage_snapshots[1].lane_index == 1
    assert state.stage_snapshots[5].sub_question == "Sub-question B?"
    assert state.stage_snapshots[5].lane_index == 2
    assert state.stage_snapshots[-1].output == "Final from 2 subanswers."
    assert captured_flush == {}


def test_run_parallel_graph_runner_is_deterministic_across_repeat_runs(monkeypatch) -> None:
    def fake_run_decomposition_node(*, node_input, model=None, timeout_s=None, callbacks=None):
        _ = node_input, model, timeout_s, callbacks
        return agent_service.DecomposeNodeOutput(
            decomposition_sub_questions=["Sub-question A?", "Sub-question B?"]
        )

    def fake_run_expand_node(*, node_input, model=None, config=None, callbacks=None):
        _ = model, config, callbacks
        if node_input.sub_question == "Sub-question A?":
            time.sleep(0.05)
        return agent_service.ExpandNodeOutput(
            expanded_queries=[node_input.sub_question, f"{node_input.sub_question} alt"]
        )

    def fake_run_search_node(*, node_input, vector_store, k_fetch=None):
        _ = vector_store, k_fetch
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Doc for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Evidence for {node_input.sub_question}",
            document_id=f"doc-{node_input.sub_question}",
        )
        return agent_service.SearchNodeOutput(
            retrieved_docs=[row],
            retrieval_provenance=[{"query": node_input.sub_question, "deduped": False}],
            citation_rows_by_index={1: row},
        )

    def fake_run_rerank_node(*, node_input, config=None, callbacks=None):
        _ = config, callbacks
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Reranked for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Reranked evidence for {node_input.sub_question}",
            document_id=f"reranked-{node_input.sub_question}",
            score=0.8,
        )
        return agent_service.RerankNodeOutput(
            reranked_docs=[row],
            citation_rows_by_index={1: row},
        )

    def fake_run_answer_subquestion_node(*, node_input, callbacks=None):
        _ = callbacks
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Answer source for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Answer evidence for {node_input.sub_question}",
            document_id=f"answer-{node_input.sub_question}",
            score=0.8,
        )
        return agent_service.AnswerSubquestionNodeOutput(
            sub_answer=f"Answer for {node_input.sub_question} [1].",
            citation_indices_used=[1],
            answerable=True,
            verification_reason="grounded_in_reranked_documents",
            citation_rows_by_index={1: row},
        )

    def fake_run_synthesize_final_node(*, node_input, callbacks=None):
        _ = callbacks
        return agent_service.SynthesizeFinalNodeOutput(
            final_answer=f"Final from {len(node_input.sub_qa)} subanswers."
        )

    monkeypatch.setattr(agent_service, "run_decomposition_node", fake_run_decomposition_node)
    monkeypatch.setattr(agent_service, "run_expand_node", fake_run_expand_node)
    monkeypatch.setattr(agent_service, "run_search_node", fake_run_search_node)
    monkeypatch.setattr(agent_service, "run_rerank_node", fake_run_rerank_node)
    monkeypatch.setattr(agent_service, "run_answer_subquestion_node", fake_run_answer_subquestion_node)
    monkeypatch.setattr(agent_service, "run_synthesize_final_node", fake_run_synthesize_final_node)
    monkeypatch.setattr(agent_service, "flush_langfuse_callback_handler", lambda handler: handler)

    states = [
        agent_service.run_parallel_graph_runner(
            payload=RuntimeAgentRunRequest(query="Main question?"),
            vector_store="fake-store",
            initial_search_context=[{"rank": 1, "title": "Initial context"}],
            run_metadata=agent_service.build_graph_run_metadata(run_id="run-parallel-deterministic"),
        )
        for _ in range(3)
    ]

    serialized_states = [_serialize_agent_graph_state(state) for state in states]

    assert serialized_states == [serialized_states[0]] * 3
    assert [snapshot["stage"] for snapshot in serialized_states[0]["stage_snapshots"]] == [
        "decompose",
        "expand",
        "search",
        "rerank",
        "answer",
        "expand",
        "search",
        "rerank",
        "answer",
        "synthesize_final",
    ]


def test_run_sequential_graph_runner_is_deterministic_across_repeat_runs(monkeypatch) -> None:
    def fake_run_decomposition_node(*, node_input, model=None, timeout_s=None, callbacks=None):
        _ = node_input, model, timeout_s, callbacks
        return agent_service.DecomposeNodeOutput(
            decomposition_sub_questions=["Sub-question A?", "Sub-question B?"]
        )

    def fake_run_expand_node(*, node_input, model=None, config=None, callbacks=None):
        _ = model, config, callbacks
        return agent_service.ExpandNodeOutput(
            expanded_queries=[node_input.sub_question, f"{node_input.sub_question} alt"]
        )

    def fake_run_search_node(*, node_input, vector_store, k_fetch=None):
        _ = vector_store, k_fetch
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Doc for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Evidence for {node_input.sub_question}",
            document_id=f"doc-{node_input.sub_question}",
        )
        return agent_service.SearchNodeOutput(
            retrieved_docs=[row],
            retrieval_provenance=[{"query": node_input.sub_question, "deduped": False}],
            citation_rows_by_index={1: row},
        )

    def fake_run_rerank_node(*, node_input, config=None, callbacks=None):
        _ = config, callbacks
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Reranked for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Reranked evidence for {node_input.sub_question}",
            document_id=f"reranked-{node_input.sub_question}",
            score=0.8,
        )
        return agent_service.RerankNodeOutput(
            reranked_docs=[row],
            citation_rows_by_index={1: row},
        )

    def fake_run_answer_subquestion_node(*, node_input, callbacks=None):
        _ = callbacks
        row = agent_service.CitationSourceRow(
            citation_index=1,
            rank=1,
            title=f"Answer source for {node_input.sub_question}",
            source="wiki://doc",
            content=f"Answer evidence for {node_input.sub_question}",
            document_id=f"answer-{node_input.sub_question}",
            score=0.8,
        )
        return agent_service.AnswerSubquestionNodeOutput(
            sub_answer=f"Answer for {node_input.sub_question} [1].",
            citation_indices_used=[1],
            answerable=True,
            verification_reason="grounded_in_reranked_documents",
            citation_rows_by_index={1: row},
        )

    def fake_run_synthesize_final_node(*, node_input, callbacks=None):
        _ = callbacks
        return agent_service.SynthesizeFinalNodeOutput(
            final_answer=f"Final from {len(node_input.sub_qa)} subanswers."
        )

    monkeypatch.setattr(agent_service, "run_decomposition_node", fake_run_decomposition_node)
    monkeypatch.setattr(agent_service, "run_expand_node", fake_run_expand_node)
    monkeypatch.setattr(agent_service, "run_search_node", fake_run_search_node)
    monkeypatch.setattr(agent_service, "run_rerank_node", fake_run_rerank_node)
    monkeypatch.setattr(agent_service, "run_answer_subquestion_node", fake_run_answer_subquestion_node)
    monkeypatch.setattr(agent_service, "run_synthesize_final_node", fake_run_synthesize_final_node)
    monkeypatch.setattr(agent_service, "flush_langfuse_callback_handler", lambda handler: handler)

    states = [
        agent_service.run_sequential_graph_runner(
            payload=RuntimeAgentRunRequest(query="Main question?"),
            vector_store="fake-store",
            initial_search_context=[{"rank": 1, "title": "Initial context"}],
            run_metadata=agent_service.build_graph_run_metadata(run_id="run-sequential-deterministic"),
        )
        for _ in range(3)
    ]

    serialized_states = [_serialize_agent_graph_state(state) for state in states]

    assert serialized_states == [serialized_states[0]] * 3
    assert [item["sub_question"] for item in serialized_states[0]["sub_qa"]] == [
        "Sub-question A?",
        "Sub-question B?",
    ]


def test_runtime_runner_executes_without_db_dependency(monkeypatch) -> None:
    from schemas import RuntimeAgentRunResponse, SubQuestionAnswer

    payload = RuntimeAgentRunRequest(query="How does core runner execute?")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        agent_service,
        "run_parallel_graph_runner",
        lambda *, payload, vector_store, model, run_metadata, initial_search_context, callbacks=None, langfuse_callback=None: captured.update(
            {
                "payload_query": payload.query,
                "vector_store": vector_store,
                "initial_search_context": initial_search_context,
                "callbacks": callbacks,
                "langfuse_callback": langfuse_callback,
            }
        )
        or agent_service.build_agent_graph_state(
            main_question=payload.query,
            sub_qa=[
                SubQuestionAnswer(
                    sub_question="Core sub-question?",
                    sub_answer="Core answer [1].",
                )
            ],
            final_answer="Core final [1].",
            run_metadata=run_metadata,
        ),
    )
    monkeypatch.setattr(
        agent_service,
        "map_graph_state_to_runtime_response",
        lambda state: RuntimeAgentRunResponse(
            main_question=state.main_question,
            sub_qa=state.sub_qa,
            output=state.output,
        ),
    )

    response = runtime_runner.run_runtime_agent(payload, model="model-x", vector_store="vector-store-core")

    assert captured["payload_query"] == "How does core runner execute?"
    assert captured["vector_store"] == "vector-store-core"
    assert captured["initial_search_context"] == []
    assert response.output == "Core final [1]."
    assert response.sub_qa[0].sub_question == "Core sub-question?"


def test_run_runtime_agent_wrapper_delegates_to_runtime_runner(monkeypatch) -> None:
    from schemas import RuntimeAgentRunResponse, SubQuestionAnswer

    payload = RuntimeAgentRunRequest(query="Wrapper compatibility?")
    session = _make_session()
    captured: dict[str, object] = {}

    def fake_runtime_core(payload_arg, *, model=None, vector_store=None):
        captured["query"] = payload_arg.query
        captured["model"] = model
        captured["vector_store"] = vector_store
        return RuntimeAgentRunResponse(
            main_question=payload_arg.query,
            sub_qa=[SubQuestionAnswer(sub_question="Wrapper sub-question?", sub_answer="Wrapper answer [1].")],
            output="Wrapper output [1].",
        )

    monkeypatch.setattr(runtime_runner, "run_runtime_agent", fake_runtime_core)

    response = agent_service.run_runtime_agent(payload, db=session, model="model-y", vector_store="store-y")

    assert captured == {
        "query": "Wrapper compatibility?",
        "model": "model-y",
        "vector_store": "store-y",
    }
    assert response.output == "Wrapper output [1]."
    assert response.sub_qa[0].sub_question == "Wrapper sub-question?"


def test_runtime_cutover_sync_path_blocks_legacy_orchestration(monkeypatch) -> None:
    sentinel_model = object()
    sentinel_vector_store = object()
    captured: dict[str, object] = {}

    def fake_execute_runtime_graph(*, context, run_metadata, config=None):
        captured["query"] = context.payload.query
        captured["vector_store"] = context.vector_store
        captured["model"] = context.model
        captured["config"] = config
        return agent_service.build_agent_graph_state(
            main_question=context.payload.query,
            sub_qa=[
                agent_service.SubQuestionAnswer(
                    sub_question="Which runtime completed the request?",
                    sub_answer="The LangGraph runtime path completed the request.",
                )
            ],
            final_answer="The LangGraph runtime path completed the request.",
            run_metadata=run_metadata,
        )

    monkeypatch.setattr(runtime_runner, "execute_runtime_graph", fake_execute_runtime_graph)
    monkeypatch.setattr(
        runtime_runner.legacy_service,
        "run_parallel_graph_runner",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("legacy orchestration should not execute")),
    )

    response = runtime_runner.run_runtime_agent(
        RuntimeAgentRunRequest(query="Which runtime completed the request?"),
        model=sentinel_model,
        vector_store=sentinel_vector_store,
    )

    assert response.output == "The LangGraph runtime path completed the request."
    assert response.sub_qa[0].sub_answer == "The LangGraph runtime path completed the request."
    assert captured == {
        "query": "Which runtime completed the request?",
        "vector_store": sentinel_vector_store,
        "model": sentinel_model,
        "config": None,
    }


def test_agent_jobs_start_wrapper_delegates_to_runtime_jobs(monkeypatch) -> None:
    payload = RuntimeAgentRunRequest(query="Start wrapper delegation?")
    captured: dict[str, object] = {}

    class _Status:
        job_id = "job-123"
        run_id = "run-123"
        status = "running"

    def fake_start(payload_arg, *, model=None, vector_store=None):
        captured["query"] = payload_arg.query
        captured["model"] = model
        captured["vector_store"] = vector_store
        return _Status()

    monkeypatch.setattr(agent_jobs, "runtime_start_agent_run_job", fake_start)

    status = agent_jobs.start_agent_run_job(payload, model="model-z", vector_store="store-z")

    assert captured == {
        "query": "Start wrapper delegation?",
        "model": "model-z",
        "vector_store": "store-z",
    }
    assert status.job_id == "job-123"
    assert status.run_id == "run-123"
    assert status.status == "running"


def test_agent_jobs_get_wrapper_delegates_to_runtime_jobs(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Status:
        job_id = "job-456"
        run_id = "run-456"
        status = "success"

    def fake_get(job_id):
        captured["job_id"] = job_id
        return _Status()

    monkeypatch.setattr(agent_jobs, "runtime_get_agent_run_job", fake_get)

    status = agent_jobs.get_agent_run_job("job-456")

    assert captured == {"job_id": "job-456"}
    assert status is not None
    assert status.job_id == "job-456"
    assert status.run_id == "run-456"
    assert status.status == "success"


def test_agent_jobs_cancel_wrapper_delegates_to_runtime_jobs(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_cancel(job_id):
        captured["job_id"] = job_id
        return True

    monkeypatch.setattr(agent_jobs, "runtime_cancel_agent_run_job", fake_cancel)

    cancelled = agent_jobs.cancel_agent_run_job("job-789")

    assert cancelled is True
    assert captured == {"job_id": "job-789"}


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

    monkeypatch.setattr(
        agent_service,
        "rerank_documents",
        lambda **_: [
            reranker_service.RerankedDocumentScore(
                document=document_validation_service.RetrievedDocument(
                    rank=1,
                    title="NATO Policy Shift",
                    source="wiki://nato",
                    content="Policy changed in 2025.",
                ),
                score=0.9,
                original_rank=2,
                reranked_rank=1,
            ),
            reranker_service.RerankedDocumentScore(
                document=document_validation_service.RetrievedDocument(
                    rank=2,
                    title="General Update",
                    source="wiki://general",
                    content="Generic summary.",
                ),
                score=0.2,
                original_rank=1,
                reranked_rank=2,
            ),
        ],
    )

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

    def fake_generate_subanswer(*, sub_question: str, reranked_retrieved_output: str, callbacks=None) -> str:
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



def _make_eval_langchain_doc(*, document_id: str, title: str, source: str, content: str):
    class _EvalDoc:
        def __init__(self) -> None:
            self.metadata = {
                "document_id": document_id,
                "title": title,
                "source": source,
            }
            self.id = document_id
            self.page_content = content

    return _EvalDoc()


def test_retrieval_quality_eval_search_plus_rerank_improves_top1_and_citation_grounding_on_hard_queries(
    monkeypatch, caplog
) -> None:
    run_metadata = agent_service.build_graph_run_metadata(run_id="run-section-20-quality")
    hard_queries = [
        {
            "sub_question": "Which team won the 2025 cup final?",
            "expanded_queries": [
                "2025 cup final winner",
                "championship final 2025 winner",
            ],
            "gold_document_id": "doc-cup-2025-gold",
            "query_results": {
                "Which team won the 2025 cup final?": [
                    _make_eval_langchain_doc(
                        document_id="doc-cup-noise-1",
                        title="General Cup Recap",
                        source="wiki://cup-recap",
                        content="A broad recap with no explicit final winner.",
                    ),
                    _make_eval_langchain_doc(
                        document_id="doc-cup-2025-gold",
                        title="[GOLD] 2025 Cup Final Result",
                        source="wiki://cup-final-2025",
                        content="Team Atlas won the 2025 cup final.",
                    ),
                ],
                "2025 cup final winner": [
                    _make_eval_langchain_doc(
                        document_id="doc-cup-2025-gold",
                        title="[GOLD] 2025 Cup Final Result",
                        source="wiki://cup-final-2025",
                        content="Team Atlas won the 2025 cup final.",
                    ),
                ],
                "championship final 2025 winner": [
                    _make_eval_langchain_doc(
                        document_id="doc-cup-noise-2",
                        title="Cup Final Ticketing",
                        source="wiki://cup-ticketing",
                        content="Ticketing and venue details.",
                    )
                ],
            },
        },
        {
            "sub_question": "When did the VAT increase take effect?",
            "expanded_queries": [
                "VAT increase effective date",
                "tax policy VAT start date",
            ],
            "gold_document_id": "doc-vat-gold",
            "query_results": {
                "When did the VAT increase take effect?": [
                    _make_eval_langchain_doc(
                        document_id="doc-vat-noise-1",
                        title="VAT policy draft",
                        source="wiki://vat-draft",
                        content="Draft language without effective date.",
                    ),
                    _make_eval_langchain_doc(
                        document_id="doc-vat-gold",
                        title="[GOLD] VAT Effective Date Bulletin",
                        source="wiki://vat-effective-date",
                        content="The VAT increase took effect on 2025-03-01.",
                    ),
                ],
                "VAT increase effective date": [
                    _make_eval_langchain_doc(
                        document_id="doc-vat-gold",
                        title="[GOLD] VAT Effective Date Bulletin",
                        source="wiki://vat-effective-date",
                        content="The VAT increase took effect on 2025-03-01.",
                    ),
                    _make_eval_langchain_doc(
                        document_id="doc-vat-noise-2",
                        title="VAT Press Q&A",
                        source="wiki://vat-qa",
                        content="Commentary around VAT changes.",
                    ),
                ],
                "tax policy VAT start date": [
                    _make_eval_langchain_doc(
                        document_id="doc-vat-noise-2",
                        title="VAT Press Q&A",
                        source="wiki://vat-qa",
                        content="Commentary around VAT changes.",
                    )
                ],
            },
        },
    ]

    query_to_documents: dict[str, list[object]] = {}
    expansions_by_sub_question: dict[str, list[str]] = {}
    gold_by_sub_question: dict[str, str] = {}
    for case in hard_queries:
        expansions_by_sub_question[case["sub_question"]] = list(case["expanded_queries"])
        gold_by_sub_question[case["sub_question"]] = str(case["gold_document_id"])
        query_to_documents.update(case["query_results"])

    monkeypatch.setattr(
        agent_service,
        "expand_queries_for_subquestion",
        lambda *, sub_question, model, config, callbacks=None: list(expansions_by_sub_question[sub_question]),
    )
    monkeypatch.setattr(
        agent_service,
        "search_documents_for_queries",
        lambda *, vector_store, queries, k, score_threshold: {
            query: list(query_to_documents.get(query, []))
            for query in queries
        },
    )

    def fake_rerank_documents(*, query, documents, config, callbacks=None):
        _ = config
        ordered = sorted(
            list(documents),
            key=lambda item: 0 if item.title.startswith("[GOLD]") else 1,
        )
        return [
            reranker_service.RerankedDocumentScore(
                document=document_validation_service.RetrievedDocument(
                    rank=rank,
                    title=item.title,
                    source=item.source,
                    content=item.content,
                ),
                score=float(len(ordered) - rank + 1),
                original_rank=item.rank,
                reranked_rank=rank,
            )
            for rank, item in enumerate(ordered, start=1)
        ]

    monkeypatch.setattr(agent_service, "rerank_documents", fake_rerank_documents)
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output, callbacks=None: "Grounded answer [1].",
    )
    monkeypatch.setattr(
        agent_service,
        "verify_subanswer",
        lambda *, sub_question, sub_answer, reranked_retrieved_output: agent_service.SubanswerVerificationResult(
            answerable=True,
            reason="grounded_in_reranked_documents",
        ),
    )

    def run_eval_slice(*, use_expansion: bool, use_rerank: bool) -> tuple[int, int]:
        top1_hits = 0
        citation_grounded_hits = 0
        for case in hard_queries:
            sub_question = str(case["sub_question"])
            expanded_queries = [sub_question]
            if use_expansion:
                expand_output = agent_service.run_expand_node(
                    node_input=ExpandNodeInput(
                        main_question=sub_question,
                        sub_question=sub_question,
                        run_metadata=run_metadata,
                    ),
                )
                expanded_queries = list(expand_output.expanded_queries)
            search_output = agent_service.run_search_node(
                node_input=SearchNodeInput(
                    sub_question=sub_question,
                    expanded_queries=expanded_queries,
                    run_metadata=run_metadata,
                ),
                vector_store="fake-vector-store",
                k_fetch=4,
            )

            candidate_rows = list(search_output.retrieved_docs)
            citation_rows_by_index = dict(search_output.citation_rows_by_index)
            if use_rerank:
                rerank_output = agent_service.run_rerank_node(
                    node_input=RerankNodeInput(
                        sub_question=sub_question,
                        retrieved_docs=[row.model_copy(deep=True) for row in search_output.retrieved_docs],
                        run_metadata=run_metadata,
                    ),
                    config=reranker_service.RerankerConfig(enabled=True, top_n=None),
                )
                candidate_rows = list(rerank_output.reranked_docs)
                citation_rows_by_index = dict(rerank_output.citation_rows_by_index)

            if candidate_rows and candidate_rows[0].document_id == gold_by_sub_question[sub_question]:
                top1_hits += 1

            answer_output = agent_service.run_answer_subquestion_node(
                node_input=AnswerSubquestionNodeInput(
                    sub_question=sub_question,
                    reranked_docs=[row.model_copy(deep=True) for row in candidate_rows],
                    citation_rows_by_index={
                        key: value.model_copy(deep=True)
                        for key, value in citation_rows_by_index.items()
                    },
                    run_metadata=run_metadata,
                )
            )
            if answer_output.answerable and answer_output.citation_indices_used:
                cited_index = answer_output.citation_indices_used[0]
                cited_row = answer_output.citation_rows_by_index.get(cited_index)
                if (
                    cited_row is not None
                    and cited_row.document_id == gold_by_sub_question[sub_question]
                ):
                    citation_grounded_hits += 1
        return top1_hits, citation_grounded_hits

    with caplog.at_level(logging.INFO):
        baseline_top1, baseline_citation = run_eval_slice(use_expansion=False, use_rerank=False)
        full_stack_top1, full_stack_citation = run_eval_slice(use_expansion=True, use_rerank=True)

    assert baseline_top1 == 0
    assert full_stack_top1 == len(hard_queries)
    assert baseline_citation == 0
    assert full_stack_citation == len(hard_queries)
    assert "Search node complete" in caplog.text
    assert "Rerank node complete" in caplog.text


def test_retrieval_quality_eval_slice_comparison_multiquery_vs_no_expand_baseline(
    monkeypatch,
) -> None:
    run_metadata = agent_service.build_graph_run_metadata(run_id="run-section-20-slices")
    sub_question = "What policy update introduced the compliance deadline?"
    gold_document_id = "doc-compliance-gold"
    query_results = {
        sub_question: [
            _make_eval_langchain_doc(
                document_id="doc-compliance-noise",
                title="Policy summary memo",
                source="wiki://compliance-memo",
                content="Overview without concrete deadline.",
            )
        ],
        "compliance deadline policy update": [
            _make_eval_langchain_doc(
                document_id=gold_document_id,
                title="[GOLD] Compliance Deadline Circular",
                source="wiki://compliance-circular",
                content="The compliance deadline is September 30, 2025.",
            )
        ],
    }

    monkeypatch.setattr(
        agent_service,
        "expand_queries_for_subquestion",
        lambda *, sub_question, main_question, model, config: ["compliance deadline policy update"],
    )
    monkeypatch.setattr(
        agent_service,
        "search_documents_for_queries",
        lambda *, vector_store, queries, k, score_threshold: {
            query: list(query_results.get(query, []))
            for query in queries
        },
    )
    monkeypatch.setattr(
        agent_service,
        "rerank_documents",
        lambda *, query, documents, config, callbacks=None: [
            reranker_service.RerankedDocumentScore(
                document=document_validation_service.RetrievedDocument(
                    rank=index,
                    title=item.title,
                    source=item.source,
                    content=item.content,
                ),
                score=float(len(selected_documents) - index + 1),
                original_rank=item.rank,
                reranked_rank=index,
            )
            for index, item in enumerate(
                (
                    lambda ordered: ordered
                    if config.top_n is None
                    else ordered[: config.top_n]
                )(
                    sorted(
                        list(documents),
                        key=lambda row: 0 if row.title.startswith("[GOLD]") else 1,
                    )
                ),
                start=1,
            )
            for selected_documents in [[
                (
                    lambda ordered: ordered
                    if config.top_n is None
                    else ordered[: config.top_n]
                )(
                    sorted(
                        list(documents),
                        key=lambda row: 0 if row.title.startswith("[GOLD]") else 1,
                    )
                )
            ][0]]
        ],
    )

    def evaluate_slice(*, expanded_queries: list[str], rerank: bool) -> tuple[str, bool]:
        search_output = agent_service.run_search_node(
            node_input=SearchNodeInput(
                sub_question=sub_question,
                expanded_queries=expanded_queries,
                run_metadata=run_metadata,
            ),
            vector_store="fake-vector-store",
            k_fetch=4,
        )
        if not rerank:
            doc_ids = [row.document_id for row in search_output.retrieved_docs]
            return search_output.retrieved_docs[0].document_id, gold_document_id in doc_ids
        rerank_output = agent_service.run_rerank_node(
            node_input=RerankNodeInput(
                sub_question=sub_question,
                retrieved_docs=[row.model_copy(deep=True) for row in search_output.retrieved_docs],
                run_metadata=run_metadata,
            ),
            config=reranker_service.RerankerConfig(enabled=True, top_n=None),
        )
        doc_ids = [row.document_id for row in rerank_output.reranked_docs]
        return rerank_output.reranked_docs[0].document_id, gold_document_id in doc_ids

    no_expand_baseline_top1, no_expand_baseline_contains_gold = evaluate_slice(
        expanded_queries=[sub_question], rerank=False
    )
    multiquery_only_top1, multiquery_only_contains_gold = evaluate_slice(
        expanded_queries=[sub_question, "compliance deadline policy update"],
        rerank=False,
    )
    multiquery_rerank_top1, multiquery_rerank_contains_gold = evaluate_slice(
        expanded_queries=[sub_question, "compliance deadline policy update"],
        rerank=True,
    )

    assert no_expand_baseline_top1 != gold_document_id
    assert no_expand_baseline_contains_gold is False
    assert multiquery_only_contains_gold is True
    assert multiquery_only_top1 != gold_document_id
    assert multiquery_rerank_contains_gold is True
    assert multiquery_rerank_top1 == gold_document_id


def _estimate_context_token_budget(rows: list[CitationSourceRow]) -> int:
    return sum(
        len(f"{row.title} {row.source} {row.content}".split())
        for row in rows
    )


def test_efficiency_eval_reranked_top_n_reduces_context_tokens_while_preserving_quality_floor(
    monkeypatch, caplog
) -> None:
    run_metadata = agent_service.build_graph_run_metadata(run_id="run-section-21-efficiency")
    sub_question = "What date did the compliance filing requirement begin?"
    gold_document_id = "doc-efficiency-gold"

    noisy_docs = [
        _make_eval_langchain_doc(
            document_id=f"doc-efficiency-noise-{index}",
            title=f"Noise memo {index}",
            source=f"wiki://noise-{index}",
            content=("Background policy discussion without the exact filing date. " * 20).strip(),
        )
        for index in range(1, 6)
    ]
    gold_doc = _make_eval_langchain_doc(
        document_id=gold_document_id,
        title="[GOLD] Filing Requirement Effective Date",
        source="wiki://filing-effective-date",
        content=("The compliance filing requirement began on 2025-10-01. " * 20).strip(),
    )
    supporting_doc = _make_eval_langchain_doc(
        document_id="doc-efficiency-support",
        title="Compliance bulletin",
        source="wiki://compliance-bulletin",
        content=("Agency bulletin confirms the filing date and rollout process. " * 20).strip(),
    )

    search_result_rows = noisy_docs + [gold_doc, supporting_doc]
    query_results = {
        sub_question: list(search_result_rows),
    }

    monkeypatch.setattr(
        agent_service,
        "search_documents_for_queries",
        lambda *, vector_store, queries, k, score_threshold: {
            query: list(query_results.get(query, []))[:k]
            for query in queries
        },
    )
    def fake_rerank_documents(*, query, documents, config, callbacks=None):
        _ = query
        ordered = sorted(
            list(documents),
            key=lambda row: 0 if row.title.startswith("[GOLD]") else 1,
        )
        selected = ordered if config.top_n is None else ordered[: config.top_n]
        return [
            reranker_service.RerankedDocumentScore(
                document=document_validation_service.RetrievedDocument(
                    rank=index,
                    title=item.title,
                    source=item.source,
                    content=item.content,
                ),
                score=float(len(selected) - index + 1),
                original_rank=item.rank,
                reranked_rank=index,
            )
            for index, item in enumerate(selected, start=1)
        ]

    monkeypatch.setattr(agent_service, "rerank_documents", fake_rerank_documents)
    monkeypatch.setattr(
        agent_service,
        "generate_subanswer",
        lambda *, sub_question, reranked_retrieved_output, callbacks=None: "The filing requirement started on 2025-10-01 [1].",
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
        search_output = agent_service.run_search_node(
            node_input=SearchNodeInput(
                sub_question=sub_question,
                expanded_queries=[sub_question],
                run_metadata=run_metadata,
            ),
            vector_store="fake-vector-store",
            k_fetch=7,
        )
        rerank_output = agent_service.run_rerank_node(
            node_input=RerankNodeInput(
                sub_question=sub_question,
                retrieved_docs=[row.model_copy(deep=True) for row in search_output.retrieved_docs],
                run_metadata=run_metadata,
            ),
            config=reranker_service.RerankerConfig(enabled=True, top_n=2),
        )
        answer_output = agent_service.run_answer_subquestion_node(
            node_input=AnswerSubquestionNodeInput(
                sub_question=sub_question,
                reranked_docs=[row.model_copy(deep=True) for row in rerank_output.reranked_docs],
                citation_rows_by_index={
                    key: value.model_copy(deep=True)
                    for key, value in rerank_output.citation_rows_by_index.items()
                },
                run_metadata=run_metadata,
            )
        )

    naive_token_budget = _estimate_context_token_budget(list(search_output.retrieved_docs))
    reranked_token_budget = _estimate_context_token_budget(list(rerank_output.reranked_docs))

    assert reranked_token_budget < naive_token_budget
    assert reranked_token_budget <= int(naive_token_budget * 0.5)
    assert any(row.document_id == gold_document_id for row in rerank_output.reranked_docs)
    assert answer_output.answerable is True
    assert answer_output.citation_indices_used == [1]
    assert answer_output.citation_rows_by_index[1].document_id == gold_document_id
    assert "Search node complete" in caplog.text
    assert "Rerank node complete" in caplog.text
    assert "Subanswer node complete" in caplog.text


def test_efficiency_eval_operating_ranges_identify_k_fetch_and_top_n_targets(
    monkeypatch, caplog
) -> None:
    run_metadata = agent_service.build_graph_run_metadata(run_id="run-section-21-operating-ranges")
    sub_question = "When does the benefit renewal policy begin?"
    gold_document_id = "doc-range-gold"

    query_rows = [
        _make_eval_langchain_doc(
            document_id=f"doc-range-noise-{index}",
            title=f"Noise source {index}",
            source=f"wiki://range-noise-{index}",
            content=("General renewal background without launch date. " * 18).strip(),
        )
        for index in range(1, 6)
    ]
    query_rows.append(
        _make_eval_langchain_doc(
            document_id=gold_document_id,
            title="[GOLD] Benefit Renewal Launch Notice",
            source="wiki://benefit-renewal-launch",
            content=("The benefit renewal policy begins on 2025-09-15. " * 18).strip(),
        )
    )
    query_rows.extend(
        [
            _make_eval_langchain_doc(
                document_id=f"doc-range-noise-tail-{index}",
                title=f"Noise tail {index}",
                source=f"wiki://range-noise-tail-{index}",
                content=("Additional policy commentary without launch date. " * 18).strip(),
            )
            for index in range(1, 3)
        ]
    )

    monkeypatch.setattr(
        agent_service,
        "search_documents_for_queries",
        lambda *, vector_store, queries, k, score_threshold: {
            query: list(query_rows)[:k]
            for query in queries
        },
    )
    def fake_rerank_documents(*, query, documents, config, callbacks=None):
        _ = query
        ordered = sorted(
            list(documents),
            key=lambda row: 0 if row.title.startswith("[GOLD]") else 1,
        )
        selected = ordered if config.top_n is None else ordered[: config.top_n]
        return [
            reranker_service.RerankedDocumentScore(
                document=document_validation_service.RetrievedDocument(
                    rank=index,
                    title=item.title,
                    source=item.source,
                    content=item.content,
                ),
                score=float(len(selected) - index + 1),
                original_rank=item.rank,
                reranked_rank=index,
            )
            for index, item in enumerate(selected, start=1)
        ]

    monkeypatch.setattr(agent_service, "rerank_documents", fake_rerank_documents)

    candidate_ranges: list[tuple[int, int]] = []
    for k_fetch in (4, 6, 8):
        for top_n in (2, 3, 5):
            with caplog.at_level(logging.INFO):
                search_output = agent_service.run_search_node(
                    node_input=SearchNodeInput(
                        sub_question=sub_question,
                        expanded_queries=[sub_question],
                        run_metadata=run_metadata,
                    ),
                    vector_store="fake-vector-store",
                    k_fetch=k_fetch,
                )
                rerank_output = agent_service.run_rerank_node(
                    node_input=RerankNodeInput(
                        sub_question=sub_question,
                        retrieved_docs=[row.model_copy(deep=True) for row in search_output.retrieved_docs],
                        run_metadata=run_metadata,
                    ),
                    config=reranker_service.RerankerConfig(enabled=True, top_n=top_n),
                )

            naive_budget = _estimate_context_token_budget(list(search_output.retrieved_docs))
            reranked_budget = _estimate_context_token_budget(list(rerank_output.reranked_docs))
            quality_floor_met = any(
                row.document_id == gold_document_id
                for row in rerank_output.reranked_docs
            )
            efficiency_ratio = reranked_budget / max(1, naive_budget)
            if quality_floor_met and efficiency_ratio <= 0.6:
                candidate_ranges.append((k_fetch, top_n))

    assert set(candidate_ranges) == {(6, 2), (6, 3), (8, 2), (8, 3)}
    assert "Search node complete" in caplog.text
    assert "Rerank node complete" in caplog.text


def test_execute_idempotent_effect_replays_completed_outcome_without_reinvoking_operation(monkeypatch) -> None:
    session_factory = _make_runtime_session_factory()
    monkeypatch.setattr(idempotency_service, "SessionLocal", session_factory)
    call_count = {"count": 0}

    def effect_fn() -> dict[str, object]:
        call_count["count"] += 1
        return {"status": "ok", "value": 7}

    first = idempotency_service.execute_idempotent_effect(
        run_id="run-idempotent",
        thread_id="550e8400-e29b-41d4-a716-446655440201",
        node_name="test-node",
        effect_key="effect-1",
        request_payload={"query": "What changed?"},
        effect_fn=effect_fn,
    )
    second = idempotency_service.execute_idempotent_effect(
        run_id="run-idempotent",
        thread_id="550e8400-e29b-41d4-a716-446655440201",
        node_name="test-node",
        effect_key="effect-1",
        request_payload={"query": "What changed?"},
        effect_fn=effect_fn,
    )

    assert call_count["count"] == 1
    assert first.replayed is False
    assert second.replayed is True
    assert second.response_payload == {"status": "ok", "value": 7}


def test_run_checkpointed_agent_retry_replays_recorded_outcome_without_duplicate_execution(monkeypatch) -> None:
    session_factory = _make_runtime_session_factory()
    monkeypatch.setattr(idempotency_service, "SessionLocal", session_factory)
    call_count = {"count": 0}
    thread_id = "550e8400-e29b-41d4-a716-446655440202"

    def fake_run_parallel_graph_runner(
        *,
        payload,
        vector_store,
        model,
        run_metadata,
        initial_search_context,
        callbacks=None,
        langfuse_callback=None,
        snapshot_callback=None,
    ):
        _ = (payload, vector_store, model, initial_search_context, callbacks, langfuse_callback, snapshot_callback)
        call_count["count"] += 1
        return agent_service.build_agent_graph_state(
            main_question="What changed?",
            decomposition_sub_questions=["What changed?"],
            sub_qa=[
                agent_service.SubQuestionAnswer(
                    sub_question="What changed?",
                    sub_answer="The rule changed.",
                )
            ],
            final_answer="The rule changed.",
            run_metadata=run_metadata,
        )

    monkeypatch.setattr(runtime_runner.legacy_service, "run_parallel_graph_runner", fake_run_parallel_graph_runner)

    compiled_graph = runtime_runner._LegacyCompiledGraph(
        payload=RuntimeAgentRunRequest(query="What changed?", thread_id=thread_id),
        vector_store="vector-store",
        model="model",
        run_metadata=agent_service.build_graph_run_metadata(run_id="run-retry", thread_id=thread_id),
        callbacks=None,
        langfuse_callback=None,
        initial_search_context=[],
        snapshot_callback=None,
    )

    first = compiled_graph.invoke(
        RuntimeAgentRunRequest(query="What changed?", thread_id=thread_id),
        config={"configurable": {"thread_id": thread_id}},
    )
    second = compiled_graph.invoke(
        RuntimeAgentRunRequest(query="What changed?", thread_id=thread_id),
        config={"configurable": {"thread_id": thread_id}},
    )

    assert call_count["count"] == 1
    assert first.response is not None
    assert second.response is not None
    assert first.response.output == "The rule changed."
    assert second.response.output == "The rule changed."
    assert second.state is not None
    assert second.state.final_answer == "The rule changed."


def test_run_checkpointed_agent_replay_is_scoped_by_thread_identity(monkeypatch) -> None:
    session_factory = _make_runtime_session_factory()
    monkeypatch.setattr(idempotency_service, "SessionLocal", session_factory)
    call_count = {"count": 0}

    def fake_run_parallel_graph_runner(
        *,
        payload,
        vector_store,
        model,
        run_metadata,
        initial_search_context,
        callbacks=None,
        langfuse_callback=None,
        snapshot_callback=None,
    ):
        _ = (vector_store, model, initial_search_context, callbacks, langfuse_callback, snapshot_callback)
        call_count["count"] += 1
        return agent_service.build_agent_graph_state(
            main_question=payload.query,
            decomposition_sub_questions=[payload.query],
            sub_qa=[
                agent_service.SubQuestionAnswer(
                    sub_question=payload.query,
                    sub_answer=f"Answered for {run_metadata.thread_id}.",
                )
            ],
            final_answer=f"Answered for {run_metadata.thread_id}.",
            run_metadata=run_metadata,
        )

    monkeypatch.setattr(runtime_runner.legacy_service, "run_parallel_graph_runner", fake_run_parallel_graph_runner)

    payload_one = RuntimeAgentRunRequest(
        query="What changed?",
        thread_id="550e8400-e29b-41d4-a716-446655440203",
    )
    payload_two = RuntimeAgentRunRequest(
        query="What changed?",
        thread_id="550e8400-e29b-41d4-a716-446655440204",
    )

    first = runtime_runner.run_checkpointed_agent(
        payload_one,
        model="model",
        vector_store="vector-store",
        run_metadata=agent_service.build_graph_run_metadata(run_id="run-thread-1", thread_id=payload_one.thread_id),
    )
    replay = runtime_runner.run_checkpointed_agent(
        payload_one,
        model="model",
        vector_store="vector-store",
        run_metadata=agent_service.build_graph_run_metadata(run_id="run-thread-1", thread_id=payload_one.thread_id),
    )
    second_thread = runtime_runner.run_checkpointed_agent(
        payload_two,
        model="model",
        vector_store="vector-store",
        run_metadata=agent_service.build_graph_run_metadata(run_id="run-thread-2", thread_id=payload_two.thread_id),
    )

    assert call_count["count"] == 2
    assert first.response is not None
    assert replay.response is not None
    assert second_thread.response is not None
    assert first.response.output == "Answered for 550e8400-e29b-41d4-a716-446655440203."
    assert replay.response.output == first.response.output
    assert second_thread.response.output == "Answered for 550e8400-e29b-41d4-a716-446655440204."
