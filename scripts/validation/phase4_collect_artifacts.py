from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
PHASE_DIR = ROOT_DIR / ".planning/phases/04-observability-and-remote-runtime-validation"
MATRIX_PATH = PHASE_DIR / "04-VALIDATION-MATRIX.md"


@dataclass(frozen=True)
class ValidationEnvironment:
    name: str
    artifact_dir: Path


ENVIRONMENTS = (
    ValidationEnvironment(
        name="remote-compose",
        artifact_dir=PHASE_DIR / "artifacts/remote-compose",
    ),
    ValidationEnvironment(
        name="pip-sdk",
        artifact_dir=PHASE_DIR / "artifacts/pip-sdk",
    ),
)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _relpath(path: Path) -> str:
    return path.relative_to(ROOT_DIR).as_posix()


def _status(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def _event_types(payload: dict[str, Any]) -> list[str]:
    correlation = payload.get("correlation", {})
    event_types = correlation.get("event_types", [])
    if isinstance(event_types, list):
        return [str(item) for item in event_types]
    return []


def _build_checks(payload: dict[str, Any], *, events_present: bool, sse_present: bool) -> dict[str, bool]:
    assertions = payload.get("assertions", {})
    start = payload.get("start", {})
    terminal = payload.get("terminal_status", {})
    correlation = payload.get("correlation", {})
    event_types = _event_types(payload)

    run_id = start.get("run_id")
    thread_id = start.get("thread_id")
    trace_id = correlation.get("trace_id")

    health_passed = bool(assertions.get("health_passed"))
    run_passed = bool(assertions.get("run_passed")) and terminal.get("status") == "success"
    lifecycle_passed = (
        bool(assertions.get("lifecycle_passed"))
        and correlation.get("event_count", 0) >= 3
        and bool(event_types)
        and event_types[0] == "run.started"
        and event_types[-1] == "run.completed"
        and events_present
    )
    correlation_passed = (
        bool(assertions.get("correlation_passed"))
        and bool(run_id)
        and bool(thread_id)
        and bool(trace_id)
        and start.get("run_id") == terminal.get("run_id") == correlation.get("run_id")
        and start.get("thread_id") == terminal.get("thread_id") == correlation.get("thread_id")
    )
    overall_passed = (
        health_passed
        and run_passed
        and lifecycle_passed
        and correlation_passed
        and bool(assertions.get("all_passed"))
        and (sse_present or payload.get("environment") == "pip-sdk")
    )

    return {
        "health": health_passed,
        "run": run_passed,
        "lifecycle": lifecycle_passed,
        "correlation": correlation_passed,
        "overall": overall_passed,
    }


def _load_environment(environment: ValidationEnvironment) -> dict[str, Any]:
    validation_path = environment.artifact_dir / "validation.json"
    if not validation_path.exists():
        raise FileNotFoundError(f"missing validation artifact: {validation_path}")

    payload = _load_json(validation_path)
    events_path = environment.artifact_dir / "events.ndjson"
    sse_path = environment.artifact_dir / "events.sse"
    checks = _build_checks(
        payload,
        events_present=events_path.exists(),
        sse_present=sse_path.exists(),
    )
    return {
        "name": environment.name,
        "payload": payload,
        "validation_path": validation_path,
        "events_path": events_path,
        "sse_path": sse_path,
        "checks": checks,
    }


def _criterion_rows(environments: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    by_name = {env["name"]: env for env in environments}
    return [
        (
            "REL-05 environment health",
            _status(by_name["remote-compose"]["checks"]["health"]),
            _status(by_name["pip-sdk"]["checks"]["health"]),
        ),
        (
            "End-to-end query run succeeds",
            _status(by_name["remote-compose"]["checks"]["run"]),
            _status(by_name["pip-sdk"]["checks"]["run"]),
        ),
        (
            "Lifecycle stream evidence captured",
            _status(by_name["remote-compose"]["checks"]["lifecycle"]),
            _status(by_name["pip-sdk"]["checks"]["lifecycle"]),
        ),
        (
            "run_id/thread_id/trace_id correlation tuple preserved",
            _status(by_name["remote-compose"]["checks"]["correlation"]),
            _status(by_name["pip-sdk"]["checks"]["correlation"]),
        ),
        (
            "REL-05 validation outcome",
            _status(by_name["remote-compose"]["checks"]["overall"]),
            _status(by_name["pip-sdk"]["checks"]["overall"]),
        ),
    ]


def _render_environment_details(environment: dict[str, Any]) -> str:
    payload = environment["payload"]
    correlation = payload["correlation"]
    start = payload["start"]
    terminal = payload["terminal_status"]
    checks = environment["checks"]
    lines = [
        f"## {environment['name']}",
        "",
        f"- Status: {_status(checks['overall'])}",
        f"- checked_at: `{payload['checked_at']}`",
        f"- run_id: `{correlation['run_id']}`",
        f"- thread_id: `{correlation['thread_id']}`",
        f"- trace_id: `{correlation['trace_id']}`",
        f"- job_id: `{start['job_id']}`",
        f"- terminal_status: `{terminal['status']}`",
        f"- event_count: `{correlation['event_count']}`",
        f"- event_types: `{', '.join(_event_types(payload))}`",
        f"- validation_json: `{_relpath(environment['validation_path'])}`",
        f"- events_ndjson: `{_relpath(environment['events_path'])}`",
    ]
    if environment["sse_path"].exists():
        lines.append(f"- events_sse: `{_relpath(environment['sse_path'])}`")
    lines.extend(
        [
            "",
            "| Criterion | Result | Evidence |",
            "| --- | --- | --- |",
            f"| Health | {_status(checks['health'])} | `validation.json` health/assertions |",
            f"| E2E run | {_status(checks['run'])} | `start.run_id={start['run_id']}` -> `terminal_status.status={terminal['status']}` |",
            f"| Lifecycle stream | {_status(checks['lifecycle'])} | `event_count={correlation['event_count']}` with `{_event_types(payload)[0]}` -> `{_event_types(payload)[-1]}` |",
            f"| Correlation | {_status(checks['correlation'])} | `run_id={correlation['run_id']}`, `thread_id={correlation['thread_id']}`, `trace_id={correlation['trace_id']}` |",
            "",
        ]
    )
    return "\n".join(lines)


def _render_matrix(environments: list[dict[str, Any]]) -> str:
    criterion_rows = _criterion_rows(environments)
    lines = [
        "# Phase 4 Validation Matrix",
        "",
        "Evidence-backed REL-05 validation for the required remote Compose and fresh pip SDK environments.",
        "",
        f"Generated at: `{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}`",
        "",
        "| Criterion | remote-compose | pip-sdk |",
        "| --- | --- | --- |",
    ]
    for criterion, compose_status, sdk_status in criterion_rows:
        lines.append(f"| {criterion} | {compose_status} | {sdk_status} |")
    lines.extend([""])
    for environment in environments:
        lines.append(_render_environment_details(environment))
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    environments = [_load_environment(environment) for environment in ENVIRONMENTS]
    MATRIX_PATH.write_text(_render_matrix(environments), encoding="utf-8")

    failed = [env["name"] for env in environments if not env["checks"]["overall"]]
    if failed:
        print(
            f"validation matrix written to {_relpath(MATRIX_PATH)} with failures: {', '.join(failed)}",
            file=sys.stderr,
        )
        return 1

    print(f"validation matrix written to {_relpath(MATRIX_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
