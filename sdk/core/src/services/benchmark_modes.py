from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from schemas.benchmark import BenchmarkMode

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BenchmarkModeDefinition:
    mode: BenchmarkMode
    runtime_config_overrides: dict[str, Any]


_MODE_REGISTRY: dict[BenchmarkMode, BenchmarkModeDefinition] = {
    BenchmarkMode.baseline_retrieve_then_answer: BenchmarkModeDefinition(
        mode=BenchmarkMode.baseline_retrieve_then_answer,
        runtime_config_overrides={
            "rerank": {"enabled": False},
            "pipeline": {"decompose_enabled": False, "query_expansion_enabled": False},
        },
    ),
    BenchmarkMode.agentic_default: BenchmarkModeDefinition(
        mode=BenchmarkMode.agentic_default,
        runtime_config_overrides={},
    ),
    BenchmarkMode.agentic_no_rerank: BenchmarkModeDefinition(
        mode=BenchmarkMode.agentic_no_rerank,
        runtime_config_overrides={"rerank": {"enabled": False}},
    ),
    BenchmarkMode.agentic_single_query_no_decompose: BenchmarkModeDefinition(
        mode=BenchmarkMode.agentic_single_query_no_decompose,
        runtime_config_overrides={"pipeline": {"decompose_enabled": False, "query_expansion_enabled": False}},
    ),
}


def get_registered_modes() -> tuple[BenchmarkMode, ...]:
    modes = tuple(_MODE_REGISTRY.keys())
    logger.info("Benchmark mode registry snapshot mode_count=%s modes=%s", len(modes), [mode.value for mode in modes])
    return modes


def get_mode_definition(mode: BenchmarkMode) -> BenchmarkModeDefinition:
    definition = _MODE_REGISTRY[mode]
    logger.info("Benchmark mode definition resolved mode=%s has_overrides=%s", mode.value, bool(definition.runtime_config_overrides))
    return definition


def get_mode_runtime_overrides(mode: BenchmarkMode) -> dict[str, Any]:
    overrides = deepcopy(get_mode_definition(mode).runtime_config_overrides)
    logger.info("Benchmark mode runtime overrides resolved mode=%s keys=%s", mode.value, sorted(overrides.keys()))
    return overrides
