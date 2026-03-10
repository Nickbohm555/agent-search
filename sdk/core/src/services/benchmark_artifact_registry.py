from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Mapping

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT_MANIFEST_PATH = BACKEND_ROOT / "benchmarks" / "drb" / "prompts" / "manifest.json"
DEFAULT_REFERENCE_MANIFEST_PATH = BACKEND_ROOT / "benchmarks" / "drb" / "reference_reports" / "manifest.json"


class BenchmarkArtifactRegistry:
    """Resolve versioned benchmark artifacts used by evaluators."""

    def __init__(
        self,
        *,
        prompt_manifest_path: Path = DEFAULT_PROMPT_MANIFEST_PATH,
        reference_manifest_path: Path = DEFAULT_REFERENCE_MANIFEST_PATH,
    ) -> None:
        self._prompt_manifest_path = prompt_manifest_path
        self._reference_manifest_path = reference_manifest_path

    def resolve_for_run(
        self,
        *,
        dataset_id: str,
        run_id: str,
        run_metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        overrides = self._extract_overrides(run_metadata)
        prompt_artifact = self._resolve_prompt_artifact(requested_version=overrides.get("prompt_version"))
        reference_artifact = self._resolve_reference_report_artifact(
            dataset_id=dataset_id,
            requested_version=overrides.get("reference_report_version"),
            requested_path=overrides.get("reference_report_path"),
        )
        registry_metadata = {
            "prompt_manifest_path": str(self._prompt_manifest_path),
            "reference_manifest_path": str(self._reference_manifest_path),
        }
        logger.info(
            "Resolved benchmark artifacts run_id=%s dataset_id=%s prompt_version=%s reference_version=%s",
            run_id,
            dataset_id,
            prompt_artifact["version"],
            reference_artifact["version"],
        )
        return {
            "prompt": prompt_artifact,
            "reference_report": reference_artifact,
            "registry": registry_metadata,
        }

    def _resolve_prompt_artifact(self, *, requested_version: str | None) -> dict[str, Any]:
        manifest = self._load_json_file(self._prompt_manifest_path)
        prompts = manifest.get("prompts")
        if not isinstance(prompts, dict) or not prompts:
            raise ValueError(f"Prompt manifest must define non-empty 'prompts': {self._prompt_manifest_path}")

        prompt_version = requested_version or self._as_non_empty_str(manifest.get("default_prompt_version"))
        if prompt_version is None:
            raise ValueError(f"Prompt manifest missing default_prompt_version: {self._prompt_manifest_path}")

        prompt_entry = prompts.get(prompt_version)
        if not isinstance(prompt_entry, dict):
            raise ValueError(
                "Unknown prompt version in benchmark artifact registry: "
                f"version={prompt_version} path={self._prompt_manifest_path}"
            )

        template_file = self._as_non_empty_str(prompt_entry.get("template_file"))
        if template_file is None:
            raise ValueError(
                f"Prompt entry missing template_file for version={prompt_version} path={self._prompt_manifest_path}"
            )

        template_path = (self._prompt_manifest_path.parent / template_file).resolve()
        template_payload = template_path.read_text(encoding="utf-8")
        template_hash = hashlib.sha256(template_payload.encode("utf-8")).hexdigest()
        return {
            "version": prompt_version,
            "template_path": str(template_path),
            "template_sha256": template_hash,
        }

    def _resolve_reference_report_artifact(
        self,
        *,
        dataset_id: str,
        requested_version: str | None,
        requested_path: str | None,
    ) -> dict[str, Any]:
        manifest = self._load_json_file(self._reference_manifest_path)
        datasets = manifest.get("datasets")
        dataset_entry = datasets.get(dataset_id) if isinstance(datasets, dict) else None
        if not isinstance(dataset_entry, dict):
            dataset_entry = {}

        resolved_version = (
            requested_version
            or self._as_non_empty_str(dataset_entry.get("reference_version"))
            or self._as_non_empty_str(manifest.get("default_reference_version"))
        )
        resolved_path = requested_path or self._as_non_empty_str(dataset_entry.get("report_path"))

        report_sha256 = None
        if resolved_path:
            reference_path = (self._reference_manifest_path.parent / resolved_path).resolve()
            if reference_path.exists():
                payload = reference_path.read_text(encoding="utf-8")
                report_sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                resolved_path = str(reference_path)
            else:
                resolved_path = str(reference_path)
                logger.warning(
                    "Reference report path missing path=%s dataset_id=%s",
                    resolved_path,
                    dataset_id,
                )
        return {
            "version": resolved_version,
            "report_path": resolved_path,
            "report_sha256": report_sha256,
        }

    def _extract_overrides(self, run_metadata: Mapping[str, Any] | None) -> dict[str, str]:
        if not isinstance(run_metadata, Mapping):
            return {}
        raw_overrides = run_metadata.get("artifact_overrides")
        if not isinstance(raw_overrides, Mapping):
            return {}

        return {
            "prompt_version": self._as_non_empty_str(raw_overrides.get("prompt_version")) or "",
            "reference_report_version": self._as_non_empty_str(raw_overrides.get("reference_report_version")) or "",
            "reference_report_path": self._as_non_empty_str(raw_overrides.get("reference_report_path")) or "",
        }

    def _load_json_file(self, path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Manifest must contain a JSON object: {path}")
        return payload

    @staticmethod
    def _as_non_empty_str(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None
