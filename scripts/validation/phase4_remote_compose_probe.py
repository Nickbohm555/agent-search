from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None, *, timeout: int = 30) -> Any:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_health(health_url: str, *, timeout_s: int = 120) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    last_error = "health check did not start"
    while time.time() < deadline:
        try:
            payload = _http_json("GET", health_url, timeout=10)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            time.sleep(2)
            continue
        if payload == {"status": "ok"}:
            return payload
        last_error = f"unexpected payload: {payload!r}"
        time.sleep(2)
    raise RuntimeError(f"backend health check failed: {last_error}")


def _collect_sse_events(events_url: str, *, timeout: int = 300) -> tuple[list[dict[str, Any]], str]:
    request = urllib.request.Request(events_url, headers={"Accept": "text/event-stream"})
    messages: list[dict[str, Any]] = []
    raw_chunks: list[str] = []
    current: dict[str, Any] = {}

    with urllib.request.urlopen(request, timeout=timeout) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8")
            raw_chunks.append(line)
            stripped = line.rstrip("\n")
            if not stripped:
                if current:
                    messages.append(current)
                    current = {}
                continue
            field, _, value = stripped.partition(": ")
            if field == "data":
                current[field] = json.loads(value)
            else:
                current[field] = value

    if current:
        messages.append(current)
    return messages, "".join(raw_chunks)


def _wait_for_terminal_status(status_url: str, *, timeout_s: int = 300) -> dict[str, Any]:
    deadline = time.time() + timeout_s
    terminal_statuses = {"success", "error", "cancelled", "paused"}
    while time.time() < deadline:
        payload = _http_json("GET", status_url, timeout=20)
        if payload.get("status") in terminal_statuses:
            return payload
        time.sleep(1)
    raise RuntimeError("timed out waiting for terminal job status")


def _assert_compose_validation(start_payload: dict[str, Any], status_payload: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    if start_payload.get("run_id") != status_payload.get("run_id"):
        raise RuntimeError("run_id drifted between async start and terminal status")
    if start_payload.get("thread_id") != status_payload.get("thread_id"):
        raise RuntimeError("thread_id drifted between async start and terminal status")
    if status_payload.get("status") != "success":
        raise RuntimeError(f"compose validation run did not succeed: {status_payload.get('status')}")
    if len(events) < 3:
        raise RuntimeError(f"expected at least 3 lifecycle events, got {len(events)}")

    event_payloads = [message["data"] for message in events]
    tuples = {
        (
            payload.get("run_id"),
            payload.get("thread_id"),
            payload.get("trace_id"),
        )
        for payload in event_payloads
    }
    if len(tuples) != 1:
        raise RuntimeError(f"lifecycle correlation tuple drifted: {sorted(tuples)!r}")

    tuple_run_id, tuple_thread_id, tuple_trace_id = next(iter(tuples))
    if tuple_run_id != start_payload.get("run_id"):
        raise RuntimeError("lifecycle run_id does not match async start payload")
    if tuple_thread_id != start_payload.get("thread_id"):
        raise RuntimeError("lifecycle thread_id does not match async start payload")
    if not tuple_trace_id:
        raise RuntimeError("trace_id missing from lifecycle events")
    if event_payloads[0].get("event_type") != "run.started":
        raise RuntimeError("lifecycle stream did not begin with run.started")
    if event_payloads[-1].get("event_type") != "run.completed":
        raise RuntimeError("lifecycle stream did not end with run.completed")
    if not any(payload.get("event_type", "").startswith("stage.") for payload in event_payloads[1:-1]):
        raise RuntimeError("lifecycle stream did not include intermediate stage events")

    return {
        "run_id": tuple_run_id,
        "thread_id": tuple_thread_id,
        "trace_id": tuple_trace_id,
        "event_count": len(events),
        "event_types": [payload["event_type"] for payload in event_payloads],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--query", default="What does NATO stand for?")
    parser.add_argument("--thread-id", default="550e8400-e29b-41d4-a716-44665544c040")
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    health_url = f"{args.base_url}/api/health"
    start_url = f"{args.base_url}/api/agents/run-async"
    status_base_url = f"{args.base_url}/api/agents/run-status"
    events_base_url = f"{args.base_url}/api/agents/run-events"

    health_payload = _wait_for_health(health_url)
    start_payload = _http_json(
        "POST",
        start_url,
        {"query": args.query, "thread_id": args.thread_id},
        timeout=30,
    )
    events, raw_sse = _collect_sse_events(f"{events_base_url}/{start_payload['job_id']}")
    status_payload = _wait_for_terminal_status(f"{status_base_url}/{start_payload['job_id']}")
    correlation = _assert_compose_validation(start_payload, status_payload, events)

    event_payloads = [message["data"] for message in events]
    (artifact_dir / "events.ndjson").write_text(
        "\n".join(json.dumps(payload, sort_keys=True) for payload in event_payloads) + "\n",
        encoding="utf-8",
    )
    (artifact_dir / "events.sse").write_text(raw_sse, encoding="utf-8")
    result = {
        "environment": "remote-compose",
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "health": health_payload,
        "start": start_payload,
        "terminal_status": status_payload,
        "correlation": correlation,
        "artifacts": {
            "events_ndjson": str((artifact_dir / "events.ndjson").as_posix()),
            "events_sse": str((artifact_dir / "events.sse").as_posix()),
        },
        "assertions": {
            "health_passed": True,
            "run_passed": status_payload["status"] == "success",
            "lifecycle_passed": correlation["event_count"] >= 3,
            "correlation_passed": bool(correlation["trace_id"]),
            "all_passed": True,
        },
    }
    (artifact_dir / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
