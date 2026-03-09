from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class BenchmarkMode(str, Enum):
    baseline_retrieve_then_answer = "baseline_retrieve_then_answer"
    agentic_default = "agentic_default"
    agentic_no_rerank = "agentic_no_rerank"
    agentic_single_query_no_decompose = "agentic_single_query_no_decompose"


class BenchmarkRunStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelling = "cancelling"
    cancelled = "cancelled"


class BenchmarkKPI(str, Enum):
    correctness = "correctness"
    latency = "latency"


class BenchmarkExecutionMode(str, Enum):
    manual_only = "manual_only"


class BenchmarkTargets(BaseModel):
    min_correctness: float = Field(default=0.75, ge=0.0, le=1.0)
    max_latency_ms_p95: int = Field(default=30000, gt=0)
    max_cost_usd: float = Field(default=5.0, ge=0.0)


class BenchmarkObjective(BaseModel):
    primary_kpi: BenchmarkKPI = BenchmarkKPI.correctness
    secondary_kpi: BenchmarkKPI = BenchmarkKPI.latency
    execution_mode: BenchmarkExecutionMode = BenchmarkExecutionMode.manual_only
    targets: BenchmarkTargets = Field(default_factory=BenchmarkTargets)


class BenchmarkRunCreateRequest(BaseModel):
    dataset_id: str = Field(min_length=1)
    modes: list[BenchmarkMode] = Field(min_length=1)
    targets: BenchmarkTargets | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("modes", mode="before")
    @classmethod
    def _validate_modes(cls, value: Any) -> Any:
        if not isinstance(value, list):
            return value

        supported_modes = {mode.value for mode in BenchmarkMode}
        invalid_modes = sorted(
            str(item)
            for item in value
            if str(item.value if isinstance(item, BenchmarkMode) else item) not in supported_modes
        )
        if invalid_modes:
            logger.error(
                "Benchmark create request rejected invalid modes invalid_modes=%s supported_modes=%s",
                invalid_modes,
                sorted(supported_modes),
            )
            raise ValueError(f"Unsupported benchmark modes: {', '.join(invalid_modes)}")
        logger.info("Benchmark create request modes validated mode_count=%s", len(value))
        return value


class BenchmarkRunCreateResponse(BaseModel):
    run_id: str = Field(min_length=1)
    status: BenchmarkRunStatus


class BenchmarkRunListItem(BaseModel):
    run_id: str = Field(min_length=1)
    status: BenchmarkRunStatus
    dataset_id: str = Field(min_length=1)
    modes: list[BenchmarkMode] = Field(default_factory=list)
    created_at: float | None = None
    started_at: float | None = None
    finished_at: float | None = None


class BenchmarkRunListResponse(BaseModel):
    runs: list[BenchmarkRunListItem] = Field(default_factory=list)


class BenchmarkModeSummary(BaseModel):
    mode: BenchmarkMode
    completed_questions: int = Field(ge=0)
    total_questions: int = Field(ge=0)
    correctness_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    avg_latency_ms: float | None = Field(default=None, ge=0.0)
    p95_latency_ms: float | None = Field(default=None, ge=0.0)


class BenchmarkResultQualityScore(BaseModel):
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    passed: bool | None = None
    rubric_version: str | None = None
    judge_model: str | None = None
    subscores: dict[str, float] | None = None
    error: str | None = None


class BenchmarkResultStatusItem(BaseModel):
    mode: str = Field(min_length=1)
    question_id: str = Field(min_length=1)
    latency_ms: int | None = Field(default=None, ge=0)
    execution_error: str | None = None
    quality: BenchmarkResultQualityScore | None = None


class BenchmarkRunStatusResponse(BaseModel):
    run_id: str = Field(min_length=1)
    status: BenchmarkRunStatus
    dataset_id: str = Field(min_length=1)
    modes: list[BenchmarkMode] = Field(default_factory=list)
    objective: BenchmarkObjective = Field(default_factory=BenchmarkObjective)
    targets: BenchmarkTargets | None = None
    mode_summaries: list[BenchmarkModeSummary] = Field(default_factory=list)
    results: list[BenchmarkResultStatusItem] = Field(default_factory=list)
    completed_questions: int = Field(default=0, ge=0)
    total_questions: int = Field(default=0, ge=0)
    created_at: float | None = None
    started_at: float | None = None
    finished_at: float | None = None
    error: str | None = None


class BenchmarkRunCancelResponse(BaseModel):
    status: Literal["success"]
    message: str
