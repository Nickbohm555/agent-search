import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db import Base, get_db
from main import app
from models import InternalDocumentChunk
from utils.embeddings import EMBEDDING_DIM


def _embedding_size(value: object) -> int:
    if isinstance(value, str):
        stripped = value.strip().strip("[]")
        if not stripped:
            return 0
        return len([part for part in stripped.split(",") if part.strip()])
    return len(list(value))


@pytest.fixture()
def internal_data_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def internal_data_client_with_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client, testing_session_local

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.mark.smoke
def test_internal_data_load_returns_observable_counts(internal_data_client: TestClient):
    response = internal_data_client.post(
        "/api/internal-data/load",
        json={
            "source_type": "inline",
            "documents": [
                {
                    "title": "Deployment Runbook",
                    "content": "Our internal deployment runbook includes a launch checklist and rollback steps.",
                    "source_ref": "runbook://deployment",
                },
                {
                    "title": "Incident FAQ",
                    "content": "The incident FAQ covers escalation paths and communication templates.",
                    "source_ref": "runbook://incident-faq",
                },
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {
        "status",
        "source_type",
        "documents_loaded",
        "chunks_created",
    }
    assert data["status"] == "success"
    assert data["source_type"] == "inline"
    assert data["documents_loaded"] == 2
    assert data["chunks_created"] >= 2


@pytest.mark.smoke
def test_internal_retrieval_returns_loaded_content(internal_data_client: TestClient):
    load_response = internal_data_client.post(
        "/api/internal-data/load",
        json={
            "source_type": "inline",
            "documents": [
                {
                    "title": "Deployment Checklist",
                    "content": "This checklist includes preflight checks, deployment steps, and post-deploy verification.",
                    "source_ref": "internal://deployment-checklist",
                },
                {
                    "title": "Hiring Plan",
                    "content": "This document describes team hiring goals and interview loops.",
                    "source_ref": "internal://hiring-plan",
                },
            ],
        },
    )
    assert load_response.status_code == 200

    retrieve_response = internal_data_client.post(
        "/api/internal-data/retrieve",
        json={"query": "deployment checklist verification", "limit": 3},
    )

    assert retrieve_response.status_code == 200
    data = retrieve_response.json()
    assert data["query"] == "deployment checklist verification"
    assert data["total_chunks_considered"] >= 2
    assert len(data["results"]) >= 1
    assert set(data["results"][0].keys()) == {
        "chunk_id",
        "document_id",
        "document_title",
        "source_type",
        "source_ref",
        "content",
        "score",
    }
    assert all(result["source_type"] == "inline" for result in data["results"])
    assert any("deployment" in result["content"].lower() for result in data["results"])


@pytest.mark.smoke
def test_internal_retrieval_ranks_relevant_chunk_above_unrelated(internal_data_client: TestClient):
    load_response = internal_data_client.post(
        "/api/internal-data/load",
        json={
            "source_type": "inline",
            "documents": [
                {
                    "title": "Operations Memo",
                    "content": (
                        "Strait of Hormuz chokepoint shipping lane transit risk "
                        "affects tanker schedules and maritime insurance pricing."
                    ),
                    "source_ref": "internal://ops-memo",
                },
                {
                    "title": "Office Lunch Menu",
                    "content": "This memo lists cafeteria desserts and weekly salad rotations.",
                    "source_ref": "internal://lunch-menu",
                },
            ],
        },
    )
    assert load_response.status_code == 200

    retrieve_response = internal_data_client.post(
        "/api/internal-data/retrieve",
        json={"query": "shipping lane risk in the strait of hormuz", "limit": 2},
    )
    assert retrieve_response.status_code == 200

    results = retrieve_response.json()["results"]
    assert len(results) == 2
    assert "ops-memo" in (results[0]["source_ref"] or "")
    assert results[0]["score"] >= results[1]["score"]


@pytest.mark.smoke
def test_wiki_data_load_returns_observable_counts(internal_data_client: TestClient):
    response = internal_data_client.post(
        "/api/internal-data/load",
        json={
            "source_type": "wiki",
            "wiki": {
                "topic": "Strait of Hormuz",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["source_type"] == "wiki"
    assert data["documents_loaded"] >= 1
    assert data["chunks_created"] >= 1


@pytest.mark.smoke
def test_internal_data_load_persists_non_null_chunk_vectors(internal_data_client_with_session):
    internal_data_client, testing_session_local = internal_data_client_with_session
    response = internal_data_client.post(
        "/api/internal-data/load",
        json={
            "source_type": "inline",
            "documents": [
                {
                    "title": "Geo Notes",
                    "content": "Hormuz transit remains a key shipping constraint and geopolitical chokepoint.",
                    "source_ref": "internal://geo-notes",
                }
            ],
        },
    )
    assert response.status_code == 200

    with testing_session_local() as db:
        chunks = db.query(InternalDocumentChunk).all()
        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.embedding is not None
            assert _embedding_size(chunk.embedding) == EMBEDDING_DIM


@pytest.mark.smoke
def test_internal_data_load_honors_langchain_chunking_env_config(
    internal_data_client_with_session,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("INTERNAL_DATA_CHUNK_SIZE", "120")
    monkeypatch.setenv("INTERNAL_DATA_CHUNK_OVERLAP", "20")

    internal_data_client, testing_session_local = internal_data_client_with_session
    content = (
        "Segment Alpha explains deployment preflight checks for services and data stores. "
        "It includes release gates, validation scripts, and rollback ownership. "
        "Segment Beta describes smoke-test execution and post-deploy verification for APIs. "
        "Segment Gamma covers escalations, incident triage, and customer communication templates. "
        "Segment Omega captures final sign-off criteria and production handoff details."
    )
    source_ref = "internal://chunking-config-smoke"

    response = internal_data_client.post(
        "/api/internal-data/load",
        json={
            "source_type": "inline",
            "documents": [{"title": "Chunking Config Runbook", "content": content, "source_ref": source_ref}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["documents_loaded"] == 1
    assert payload["chunks_created"] >= 2

    with testing_session_local() as db:
        chunks = (
            db.query(InternalDocumentChunk)
            .filter(InternalDocumentChunk.document.has(source_ref=source_ref))
            .order_by(InternalDocumentChunk.chunk_index.asc())
            .all()
        )
        assert len(chunks) == payload["chunks_created"]
        assert chunks[0].content.startswith("Segment Alpha")
        assert "Segment Omega" in chunks[-1].content

    retrieve_response = internal_data_client.post(
        "/api/internal-data/retrieve",
        json={"query": "final sign-off criteria production handoff", "limit": 3},
    )
    assert retrieve_response.status_code == 200
    retrieval_results = retrieve_response.json()["results"]
    assert any((result["source_ref"] or "") == source_ref for result in retrieval_results)


@pytest.mark.smoke
def test_wiki_retrieval_includes_wiki_attribution_and_content(internal_data_client: TestClient):
    load_response = internal_data_client.post(
        "/api/internal-data/load",
        json={
            "source_type": "wiki",
            "wiki": {
                "url": "https://en.wikipedia.org/wiki/Strait_of_Hormuz",
            },
        },
    )
    assert load_response.status_code == 200

    retrieve_response = internal_data_client.post(
        "/api/internal-data/retrieve",
        json={"query": "Which corridor links the Persian Gulf and impacts oil shipping?", "limit": 5},
    )

    assert retrieve_response.status_code == 200
    data = retrieve_response.json()
    assert len(data["results"]) >= 1
    wiki_results = [item for item in data["results"] if item["source_type"] == "wiki"]
    assert len(wiki_results) >= 1
    assert all(len(item["document_title"].strip()) > 0 for item in wiki_results)
    assert all(len(item["content"].strip()) > 0 for item in wiki_results)
    assert any(
        item["source_ref"] == "https://en.wikipedia.org/wiki/Strait_of_Hormuz"
        for item in wiki_results
    )
