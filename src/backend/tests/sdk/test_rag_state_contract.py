from __future__ import annotations

import sys
from pathlib import Path
from typing import get_type_hints

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import RAGState as PublicRAGState
from agent_search.runtime import RAGState as RuntimeRAGState
from agent_search.runtime.state import RAGState as InternalRAGState
from schemas import GraphRunMetadata, RuntimeAgentRunResponse, SubQuestionAnswer


def test_rag_state_is_exported_from_public_sdk_entrypoints() -> None:
    assert PublicRAGState is InternalRAGState
    assert RuntimeRAGState is InternalRAGState


def test_rag_state_required_keys_match_canonical_contract() -> None:
    assert PublicRAGState.__required_keys__ == {
        "main_question",
        "decomposition_sub_questions",
        "sub_question_artifacts",
        "final_answer",
        "citation_rows_by_index",
        "run_metadata",
        "sub_qa",
        "output",
        "stage_snapshots",
    }


def test_rag_state_annotations_cover_runtime_response_fields() -> None:
    annotations = get_type_hints(PublicRAGState, include_extras=True)

    response = RuntimeAgentRunResponse(
        main_question="What changed?",
        sub_qa=[SubQuestionAnswer(sub_question="What changed?", sub_answer="The public contract exports RAGState.")],
        output="The public contract exports RAGState.",
    )

    rag_state: PublicRAGState = {
        "main_question": response.main_question,
        "decomposition_sub_questions": [],
        "sub_question_artifacts": [],
        "final_answer": response.output,
        "citation_rows_by_index": {},
        "run_metadata": GraphRunMetadata(run_id="run-123"),
        "sub_qa": response.sub_qa,
        "output": response.output,
        "stage_snapshots": [],
    }

    assert annotations["main_question"] is str
    assert "sub_qa" in annotations
    assert "output" in annotations
    assert rag_state["main_question"] == response.main_question
    assert rag_state["sub_qa"] == response.sub_qa
    assert rag_state["output"] == response.output
