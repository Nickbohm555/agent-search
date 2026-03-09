from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.runtime.nodes import expand
from schemas import ExpandNodeInput, GraphRunMetadata
from services.query_expansion_service import QueryExpansionConfig


def _node_input(sub_question: str = "What changed in VAT policy?") -> ExpandNodeInput:
    return ExpandNodeInput(
        main_question="Explain VAT changes",
        sub_question=sub_question,
        run_metadata=GraphRunMetadata(
            run_id="run-node-expand",
            trace_id="trace-node-expand",
            correlation_id="corr-node-expand",
        ),
    )


def test_run_expansion_node_returns_expander_output() -> None:
    output = expand.run_expansion_node(
        node_input=_node_input(),
        default_config=QueryExpansionConfig(
            model="gpt-4.1-mini",
            temperature=0.0,
            max_queries=4,
            max_query_length=256,
        ),
        expand_queries_fn=lambda **_kwargs: [
            "What changed in VAT policy?",
            "VAT policy updates 2025",
            "VAT changes by region",
        ],
    )

    assert output.expanded_queries == [
        "What changed in VAT policy?",
        "VAT policy updates 2025",
        "VAT changes by region",
    ]


def test_run_expansion_node_uses_provided_config_and_sub_question() -> None:
    calls: list[dict[str, object]] = []

    def _fake_expand(**kwargs):
        calls.append(kwargs)
        return ["What changed in VAT policy?"]

    output = expand.run_expansion_node(
        node_input=_node_input(),
        config=QueryExpansionConfig(
            model="custom-model",
            temperature=0.2,
            max_queries=2,
            max_query_length=42,
        ),
        default_config=QueryExpansionConfig(
            model="gpt-4.1-mini",
            temperature=0.0,
            max_queries=4,
            max_query_length=256,
        ),
        expand_queries_fn=_fake_expand,
    )

    assert output.expanded_queries == ["What changed in VAT policy?"]
    assert len(calls) == 1
    assert calls[0]["sub_question"] == "What changed in VAT policy?"
    assert calls[0]["config"] == QueryExpansionConfig(
        model="custom-model",
        temperature=0.2,
        max_queries=2,
        max_query_length=42,
    )
