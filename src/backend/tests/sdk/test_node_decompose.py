from __future__ import annotations

import sys
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime.nodes import decompose
from schemas import DecomposeNodeInput, GraphRunMetadata


def _node_input(question: str = "What changed in VAT policy?") -> DecomposeNodeInput:
    return DecomposeNodeInput(
        main_question=question,
        initial_search_context=[{"title": "Policy update", "source": "kb://policy"}],
        run_metadata=GraphRunMetadata(
            run_id="run-node-decompose",
            trace_id="trace-node-decompose",
            correlation_id="corr-node-decompose",
        ),
    )


def test_run_decomposition_node_emits_normalized_subquestions() -> None:
    output = decompose.run_decomposition_node(
        node_input=_node_input(),
        default_timeout_s=60,
        run_with_timeout_fn=lambda **kwargs: kwargs["fn"](),
        run_llm_call_fn=lambda **_kwargs: [
            "What changed in VAT policy",
            "What changed in VAT policy?",
            "  Which products were impacted   ",
            "",
        ],
    )

    assert output.decomposition_sub_questions == [
        "What changed in VAT policy?",
        "Which products were impacted?",
    ]


def test_run_decomposition_node_uses_fallback_on_timeout() -> None:
    def _timeout(**_kwargs):
        raise FuturesTimeoutError()

    output = decompose.run_decomposition_node(
        node_input=_node_input("Explain VAT changes"),
        default_timeout_s=60,
        run_with_timeout_fn=_timeout,
    )

    assert output.decomposition_sub_questions == ["Explain VAT changes?"]


def test_parse_decomposition_output_preserves_bullets_json_and_fallback() -> None:
    parsed_from_bullets = decompose._parse_decomposition_output(
        raw_output="""
            1. What changed for VAT exemptions
            - Which regions were affected?
            *  What changed for VAT exemptions?
        """,
        query="Original query",
    )
    assert parsed_from_bullets == [
        "What changed for VAT exemptions?",
        "Which regions were affected?",
    ]

    parsed_from_json = decompose._parse_decomposition_output(
        raw_output='{"sub_questions": ["What is policy X", "What is policy X?", "Who is affected"]}',
        query="Original query",
    )
    assert parsed_from_json == ["What is policy X?", "Who is affected?"]

    parsed_fallback = decompose._parse_decomposition_output(raw_output="", query="Original query")
    assert parsed_fallback == ["Original query?"]
