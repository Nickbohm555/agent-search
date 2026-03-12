from __future__ import annotations

import argparse
import importlib.metadata
import json
import time
from pathlib import Path

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores.pgvector import PGVector

from agent_search import public_api
from agent_search.runtime.jobs import iter_agent_run_events, list_agent_run_events


class DeterministicHashEmbeddings:
    def __init__(self, *, dim: int = 1536) -> None:
        self._dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_text(text)

    def _embed_text(self, text: str) -> list[float]:
        import hashlib

        seed = text.encode("utf-8")
        values: list[float] = []
        counter = 0
        while len(values) < self._dim:
            digest = hashlib.sha256(seed + counter.to_bytes(4, byteorder="big")).digest()
            for index in range(0, len(digest), 4):
                chunk = digest[index : index + 4]
                integer = int.from_bytes(chunk, byteorder="big", signed=False)
                values.append((integer / 0xFFFFFFFF) * 2.0 - 1.0)
                if len(values) == self._dim:
                    break
            counter += 1
        return values


def _build_vector_store(*, connection: str, collection_name: str) -> PGVector:
    return PGVector(
        connection_string=connection,
        collection_name=collection_name,
        embedding_function=DeterministicHashEmbeddings(),
        use_jsonb=True,
    )


def _seed_vector_store(vector_store: PGVector) -> list[str]:
    docs = [
        Document(
            page_content=(
                "NATO stands for the North Atlantic Treaty Organization. "
                "It was founded in 1949 as a collective defense alliance."
            ),
            metadata={"title": "NATO", "source": "https://example.test/sdk-nato"},
        ),
        Document(
            page_content=(
                "The North Atlantic Treaty established NATO and created a framework "
                "for collective defense among member states."
            ),
            metadata={"title": "North Atlantic Treaty", "source": "https://example.test/sdk-treaty"},
        ),
    ]
    return vector_store.add_documents(docs)


def _assert_sdk_validation(*, start_payload: dict[str, object], status_payload: dict[str, object], event_payloads: list[dict[str, object]]) -> dict[str, object]:
    if status_payload.get("status") != "success":
        raise RuntimeError(f"sdk validation run did not succeed: {status_payload.get('status')}")
    if start_payload.get("run_id") != status_payload.get("run_id"):
        raise RuntimeError("sdk run_id drifted between async start and terminal status")
    if start_payload.get("thread_id") != status_payload.get("thread_id"):
        raise RuntimeError("sdk thread_id drifted between async start and terminal status")
    if len(event_payloads) < 3:
        raise RuntimeError(f"expected at least 3 lifecycle events, got {len(event_payloads)}")

    tuples = {
        (
            payload.get("run_id"),
            payload.get("thread_id"),
            payload.get("trace_id"),
        )
        for payload in event_payloads
    }
    if len(tuples) != 1:
        raise RuntimeError(f"sdk lifecycle correlation tuple drifted: {sorted(tuples)!r}")
    tuple_run_id, tuple_thread_id, tuple_trace_id = next(iter(tuples))
    if tuple_run_id != start_payload.get("run_id"):
        raise RuntimeError("sdk lifecycle run_id does not match async start payload")
    if tuple_thread_id != start_payload.get("thread_id"):
        raise RuntimeError("sdk lifecycle thread_id does not match async start payload")
    if not tuple_trace_id:
        raise RuntimeError("sdk lifecycle trace_id missing")
    if event_payloads[0].get("event_type") != "run.started":
        raise RuntimeError("sdk lifecycle stream did not begin with run.started")
    if event_payloads[-1].get("event_type") != "run.completed":
        raise RuntimeError("sdk lifecycle stream did not end with run.completed")
    if not any(str(payload.get("event_type", "")).startswith("stage.") for payload in event_payloads[1:-1]):
        raise RuntimeError("sdk lifecycle stream did not include intermediate stage events")

    return {
        "run_id": tuple_run_id,
        "thread_id": tuple_thread_id,
        "trace_id": tuple_trace_id,
        "event_count": len(event_payloads),
        "event_types": [str(payload["event_type"]) for payload in event_payloads],
    }


def _resolve_package_version() -> str:
    try:
        return importlib.metadata.version("agent-search-backend")
    except importlib.metadata.PackageNotFoundError:
        return "source-checkout"


def _wait_for_terminal_status(job_id: str, *, timeout_s: int = 180) -> dict[str, object]:
    deadline = time.time() + timeout_s
    terminal_statuses = {"success", "error", "cancelled", "paused"}
    while time.time() < deadline:
        payload = public_api.get_run_status(job_id).model_dump(mode="json")
        if payload.get("status") in terminal_statuses:
            return payload
        time.sleep(1)
    raise RuntimeError("sdk validation timed out waiting for terminal status")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--thread-id", default="550e8400-e29b-41d4-a716-44665544c041")
    parser.add_argument("--query", default="What does NATO stand for?")
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--collection", default="phase4_sdk_validation")
    args = parser.parse_args()

    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    vector_store = _build_vector_store(connection=args.database_url, collection_name=args.collection)
    if hasattr(vector_store, "delete_collection"):
        vector_store.delete_collection()
    vector_store = _build_vector_store(connection=args.database_url, collection_name=args.collection)
    inserted_ids = _seed_vector_store(vector_store)
    probe_results = vector_store.similarity_search("NATO treaty alliance", k=1)
    if not probe_results:
        raise RuntimeError("sdk health check failed: no vector search results after seeding")

    model = ChatOpenAI(model=args.model, temperature=0.0)
    start_response = public_api.run_async(
        args.query,
        vector_store=vector_store,
        model=model,
        config={"thread_id": args.thread_id},
    )
    _ = [event.model_dump(mode="json") for event in iter_agent_run_events(start_response.job_id)]
    status_payload = _wait_for_terminal_status(start_response.job_id)
    event_payloads = [event.model_dump(mode="json") for event in list_agent_run_events(start_response.job_id)]

    start_payload = start_response.model_dump(mode="json")
    correlation = _assert_sdk_validation(
        start_payload=start_payload,
        status_payload=status_payload,
        event_payloads=event_payloads,
    )

    (artifact_dir / "events.ndjson").write_text(
        "\n".join(json.dumps(payload, sort_keys=True) for payload in event_payloads) + "\n",
        encoding="utf-8",
    )
    result = {
        "environment": "pip-sdk",
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "package": {
            "name": "agent-search-backend",
            "version": _resolve_package_version(),
            "install_mode": "clean-pip-deps-plus-source-checkout",
        },
        "health": {
            "database_url": args.database_url,
            "collection_name": args.collection,
            "seeded_documents": len(inserted_ids),
            "retrieval_probe_count": len(probe_results),
        },
        "start": start_payload,
        "terminal_status": status_payload,
        "correlation": correlation,
        "artifacts": {
            "events_ndjson": str((artifact_dir / "events.ndjson").as_posix()),
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
