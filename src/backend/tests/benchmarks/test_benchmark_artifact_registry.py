from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from models import BenchmarkRun
from schemas import BenchmarkMode, CitationSourceRow, RuntimeAgentRunResponse
from services.benchmark_artifact_registry import BenchmarkArtifactRegistry
from services.benchmark_runner import BenchmarkRunner

DATABASE_URL = "postgresql+psycopg://agent_user:agent_pass@db:5432/agent_search"


class _SuccessAdapter:
    def run_sync(self, query: str, *, vector_store, model, config=None):  # noqa: ANN001
        del vector_store, model, config
        return RuntimeAgentRunResponse(
            output=f"answer::{query}",
            final_citations=[CitationSourceRow(citation_index=1, rank=1, title="Doc", source="internal")],
        )


def _write_dataset(tmp_path: Path, dataset_id: str) -> Path:
    dataset_dir = tmp_path / "benchmarks" / "datasets" / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = dataset_dir / "questions.jsonl"
    row = {
        "question_id": "DRB-001",
        "question": "What changed in policy?",
        "domain": "policy",
        "difficulty": "easy",
        "expected_answer_points": ["point-a"],
        "required_sources": ["source-a"],
        "disallowed_behaviors": ["hallucinate"],
    }
    dataset_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    return tmp_path / "benchmarks" / "datasets"


def _write_prompt_manifest(tmp_path: Path) -> Path:
    prompt_dir = tmp_path / "benchmarks" / "drb" / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    (prompt_dir / "quality_v1.txt").write_text("judge prompt v1", encoding="utf-8")
    (prompt_dir / "quality_v2.txt").write_text("judge prompt v2", encoding="utf-8")
    (prompt_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "default_prompt_version": "v1",
                "prompts": {
                    "v1": {"template_file": "quality_v1.txt"},
                    "v2": {"template_file": "quality_v2.txt"},
                },
            }
        ),
        encoding="utf-8",
    )
    return prompt_dir / "manifest.json"


def _write_reference_manifest(tmp_path: Path) -> Path:
    root = tmp_path / "benchmarks" / "drb" / "reference_reports"
    (root / "internal_v1").mkdir(parents=True, exist_ok=True)
    (root / "internal_v1" / "report_v1.md").write_text("reference report v1", encoding="utf-8")
    (root / "custom").mkdir(parents=True, exist_ok=True)
    (root / "custom" / "override.md").write_text("reference override", encoding="utf-8")
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "default_reference_version": None,
                "datasets": {
                    "internal_v1": {
                        "reference_version": "rr-v1",
                        "report_path": "internal_v1/report_v1.md",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return root / "manifest.json"


def test_registry_resolves_default_versions_for_dataset(tmp_path: Path) -> None:
    registry = BenchmarkArtifactRegistry(
        prompt_manifest_path=_write_prompt_manifest(tmp_path),
        reference_manifest_path=_write_reference_manifest(tmp_path),
    )

    resolved = registry.resolve_for_run(dataset_id="internal_v1", run_id="run-1")

    assert resolved["prompt"]["version"] == "v1"
    assert resolved["prompt"]["template_path"].endswith("quality_v1.txt")
    assert resolved["prompt"]["template_sha256"]
    assert resolved["reference_report"]["version"] == "rr-v1"
    assert resolved["reference_report"]["report_path"].endswith("internal_v1/report_v1.md")
    assert resolved["reference_report"]["report_sha256"]


def test_registry_applies_run_level_overrides(tmp_path: Path) -> None:
    registry = BenchmarkArtifactRegistry(
        prompt_manifest_path=_write_prompt_manifest(tmp_path),
        reference_manifest_path=_write_reference_manifest(tmp_path),
    )

    resolved = registry.resolve_for_run(
        dataset_id="internal_v1",
        run_id="run-2",
        run_metadata={
            "artifact_overrides": {
                "prompt_version": "v2",
                "reference_report_version": "rr-custom",
                "reference_report_path": "custom/override.md",
            }
        },
    )

    assert resolved["prompt"]["version"] == "v2"
    assert resolved["prompt"]["template_path"].endswith("quality_v2.txt")
    assert resolved["reference_report"]["version"] == "rr-custom"
    assert resolved["reference_report"]["report_path"].endswith("custom/override.md")


def test_runner_persists_artifact_versions_in_run_metadata(tmp_path: Path) -> None:
    dataset_root = _write_dataset(tmp_path, "tiny_v1")
    artifact_registry = BenchmarkArtifactRegistry(
        prompt_manifest_path=_write_prompt_manifest(tmp_path),
        reference_manifest_path=_write_reference_manifest(tmp_path),
    )
    engine = create_engine(DATABASE_URL, future=True)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    runner = BenchmarkRunner(
        session_factory=session_factory,
        execution_adapter=_SuccessAdapter(),
        dataset_root=dataset_root,
        artifact_registry=artifact_registry,
    )
    run_id = f"run-benchmark-artifacts-{uuid.uuid4()}"

    runner.run(
        run_id=run_id,
        dataset_id="tiny_v1",
        modes=[BenchmarkMode.agentic_default],
        vector_store=object(),
        model="model-test",
        metadata={"trigger": "test"},
    )

    with Session(engine) as session:
        run = session.get(BenchmarkRun, run_id)
        assert run is not None
        assert run.run_metadata["trigger"] == "test"
        assert run.run_metadata["artifact_versions"]["prompt"]["version"] == "v1"
        assert run.run_metadata["artifact_versions"]["prompt"]["template_sha256"]
        assert run.run_metadata["artifact_versions"]["reference_report"]["version"] is None
