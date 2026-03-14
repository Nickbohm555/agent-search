from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search.config import RuntimeConfig


def test_runtime_config_defaults_preserve_current_runtime_values() -> None:
    config = RuntimeConfig.from_dict()

    assert config.timeout.vector_store_acquisition_timeout_s == 20
    assert config.timeout.initial_search_timeout_s == 20
    assert config.timeout.decomposition_llm_timeout_s == 60
    assert config.timeout.rerank_timeout_s == 1

    assert config.retrieval.initial_search_context_k == 5
    assert config.retrieval.search_node_k_fetch == 10
    assert config.retrieval.search_node_score_threshold == 0.0
    assert config.retrieval.search_node_merged_cap == 30
    assert config.retrieval.refinement_retrieval_k == 10

    assert config.rerank.enabled is True
    assert config.rerank.top_n is None
    assert config.rerank.provider == "openai"
    assert config.query_expansion.enabled is True
    assert config.hitl.enabled is False
    assert config.hitl.subquestions_enabled is False
    assert config.custom_prompts.subanswer is None
    assert config.custom_prompts.synthesis is None


def test_runtime_config_applies_nested_timeout_retrieval_and_rerank_overrides() -> None:
    config = RuntimeConfig.from_dict(
        {
            "timeout": {
                "initial_search_timeout_s": 55,
                "refined_answer_timeout_s": 75,
            },
            "retrieval": {
                "search_node_k_fetch": 25,
                "search_node_score_threshold": 0.15,
                "search_node_merged_cap": 40,
            },
            "rerank": {
                "enabled": False,
                "top_n": 8,
                "provider": "openai",
            },
            "query_expansion": {
                "enabled": False,
            },
        }
    )

    assert config.timeout.initial_search_timeout_s == 55
    assert config.timeout.refined_answer_timeout_s == 75
    assert config.retrieval.search_node_k_fetch == 25
    assert config.retrieval.search_node_score_threshold == 0.15
    assert config.retrieval.search_node_merged_cap == 40
    assert config.rerank.enabled is False
    assert config.rerank.top_n == 8
    assert config.rerank.provider == "openai"
    assert config.query_expansion.enabled is False


def test_runtime_config_falls_back_to_defaults_for_invalid_overrides() -> None:
    config = RuntimeConfig.from_dict(
        {
            "timeout": {"initial_search_timeout_s": "abc"},
            "retrieval": {"search_node_k_fetch": 0},
            "rerank": {"enabled": "maybe", "top_n": -3, "provider": "unknown-provider"},
            "query_expansion": {"enabled": "maybe"},
        }
    )

    assert config.timeout.initial_search_timeout_s == 20
    assert config.retrieval.search_node_k_fetch == 10
    assert config.rerank.enabled is True
    assert config.rerank.top_n is None
    assert config.rerank.provider == "openai"
    assert config.query_expansion.enabled is True


def test_runtime_config_falls_back_to_query_expansion_defaults_for_invalid_section_type() -> None:
    config = RuntimeConfig.from_dict({"query_expansion": "disabled"})

    assert config.query_expansion.enabled is True


def test_runtime_config_enables_hitl_when_nested_subquestions_are_enabled() -> None:
    config = RuntimeConfig.from_dict({"hitl": {"subquestions": {"enabled": True}}})

    assert config.hitl.enabled is True
    assert config.hitl.subquestions_enabled is True


def test_runtime_config_falls_back_to_hitl_defaults_for_invalid_section_type() -> None:
    config = RuntimeConfig.from_dict({"hitl": "paused"})

    assert config.hitl.enabled is False
    assert config.hitl.subquestions_enabled is False


def test_runtime_config_parses_custom_prompts_with_alias_and_ignores_unknown_keys() -> None:
    config = RuntimeConfig.from_dict(
        {
            "custom-prompts": {
                "subanswer": "Answer subquestions with concise grounded steps.",
                "synthesis": "Synthesize a final answer with citations.",
                "unexpected": "ignore me",
            }
        }
    )

    assert config.custom_prompts.subanswer == "Answer subquestions with concise grounded steps."
    assert config.custom_prompts.synthesis == "Synthesize a final answer with citations."


def test_runtime_config_parses_custom_prompts_with_canonical_snake_case() -> None:
    config = RuntimeConfig.from_dict(
        {
            "custom_prompts": {
                "subanswer": "Use grounded support for each subanswer.",
                "synthesis": "Provide a concise synthesis with citations.",
            }
        }
    )

    assert config.custom_prompts.subanswer == "Use grounded support for each subanswer."
    assert config.custom_prompts.synthesis == "Provide a concise synthesis with citations."


def test_runtime_config_preserves_legacy_defaults_when_custom_prompts_omitted() -> None:
    config = RuntimeConfig.from_dict({"rerank": {"enabled": False}})

    assert config.rerank.enabled is False
    assert config.custom_prompts.subanswer is None
    assert config.custom_prompts.synthesis is None


def test_runtime_config_ignores_invalid_custom_prompt_section_type() -> None:
    config = RuntimeConfig.from_dict({"custom_prompts": "not-a-map"})

    assert config.custom_prompts.subanswer is None
    assert config.custom_prompts.synthesis is None
