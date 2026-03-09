from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from langchain_core.documents import Document

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from agent_search import public_api
from agent_search.errors import SDKConfigurationError
from agent_search.vectorstore.protocol import VectorStoreProtocol, assert_vector_store_compatible


class _CompatibleVectorStore:
    def similarity_search(
        self,
        query: str,
        k: int,
        filter: dict[str, object] | None = None,
    ) -> list[Document]:
        return [
            Document(
                page_content=f"result for {query}",
                metadata={"source": "test://doc-1", "filter": filter},
            )
        ][:k]


class _MissingVectorStoreMethod:
    pass


class _NoFilterVectorStore:
    def similarity_search(self, query: str, k: int) -> list[Document]:
        return [Document(page_content=query, metadata={})][:k]


def test_vector_store_protocol_accepts_structurally_compatible_store() -> None:
    store = _CompatibleVectorStore()
    assert isinstance(store, VectorStoreProtocol)
    assert assert_vector_store_compatible(store) is store


def test_vector_store_protocol_rejects_missing_similarity_search() -> None:
    try:
        assert_vector_store_compatible(_MissingVectorStoreMethod())
    except SDKConfigurationError as exc:
        assert str(exc) == "vector_store must implement similarity_search(query, k, filter=None)."
    else:
        raise AssertionError("Expected SDKConfigurationError for missing method")


def test_vector_store_protocol_rejects_similarity_search_without_filter() -> None:
    try:
        assert_vector_store_compatible(_NoFilterVectorStore())
    except SDKConfigurationError as exc:
        assert str(exc) == "vector_store similarity_search must accept (query, k, filter=None)."
    else:
        raise AssertionError("Expected SDKConfigurationError for incompatible signature")


def test_run_rejects_incompatible_vector_store_before_runtime_call(monkeypatch) -> None:
    called = False

    def fake_run_runtime_agent(*_args, **_kwargs):
        nonlocal called
        called = True
        return SimpleNamespace()

    monkeypatch.setattr(public_api, "run_runtime_agent", fake_run_runtime_agent)

    try:
        public_api.run("q", model=object(), vector_store=_MissingVectorStoreMethod())
    except SDKConfigurationError as exc:
        assert str(exc) == "vector_store must implement similarity_search(query, k, filter=None)."
    else:
        raise AssertionError("Expected SDKConfigurationError for invalid vector store")

    assert called is False


def test_run_async_rejects_incompatible_vector_store_before_job_start(monkeypatch) -> None:
    called = False

    def fake_start_agent_run_job(*_args, **_kwargs):
        nonlocal called
        called = True
        return SimpleNamespace(job_id="job", run_id="run", status="running")

    monkeypatch.setattr(public_api, "start_agent_run_job", fake_start_agent_run_job)

    try:
        public_api.run_async("q", model=object(), vector_store=_MissingVectorStoreMethod())
    except SDKConfigurationError as exc:
        assert str(exc) == "vector_store must implement similarity_search(query, k, filter=None)."
    else:
        raise AssertionError("Expected SDKConfigurationError for invalid vector store")

    assert called is False
