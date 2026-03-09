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
                "provider": "flashrank",
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
    assert config.rerank.provider == "flashrank"


def test_runtime_config_falls_back_to_defaults_for_invalid_overrides() -> None:
    config = RuntimeConfig.from_dict(
        {
            "timeout": {"initial_search_timeout_s": "abc"},
            "retrieval": {"search_node_k_fetch": 0},
            "rerank": {"enabled": "maybe", "top_n": -3, "provider": "unknown-provider"},
        }
    )

    assert config.timeout.initial_search_timeout_s == 20
    assert config.retrieval.search_node_k_fetch == 10
    assert config.rerank.enabled is True
    assert config.rerank.top_n is None
    assert config.rerank.provider == "openai"
