from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class BenchmarkMode(str, Enum):
    baseline = "baseline"
    retrieval_only = "retrieval_only"
    full = "full"


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


class BenchmarkRunStatusResponse(BaseModel):
    run_id: str = Field(min_length=1)
    status: BenchmarkRunStatus
    dataset_id: str = Field(min_length=1)
    modes: list[BenchmarkMode] = Field(default_factory=list)
    objective: BenchmarkObjective = Field(default_factory=BenchmarkObjective)
    targets: BenchmarkTargets | None = None
    mode_summaries: list[BenchmarkModeSummary] = Field(default_factory=list)
    completed_questions: int = Field(default=0, ge=0)
    total_questions: int = Field(default=0, ge=0)
    created_at: float | None = None
    started_at: float | None = None
    finished_at: float | None = None
    error: str | None = None


class BenchmarkRunCancelResponse(BaseModel):
    status: Literal["success"]
    message: str
