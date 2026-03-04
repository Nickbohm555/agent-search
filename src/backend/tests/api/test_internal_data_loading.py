import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db import Base, get_db
from main import app
from utils.google_docs import GoogleDocContent


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
    assert all(result["source_type"] == "inline" for result in data["results"])
    assert any("deployment" in result["content"].lower() for result in data["results"])


@pytest.mark.smoke
def test_internal_retrieval_handles_empty_corpus(internal_data_client: TestClient):
    response = internal_data_client.post(
        "/api/internal-data/retrieve",
        json={"query": "anything", "limit": 5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_chunks_considered"] == 0
    assert data["results"] == []


@pytest.mark.smoke
def test_internal_retrieval_returns_low_signal_for_unrelated_query(internal_data_client: TestClient):
    load_response = internal_data_client.post(
        "/api/internal-data/load",
        json={
            "source_type": "inline",
            "documents": [
                {
                    "title": "Engineering Notes",
                    "content": "Service owners rotate weekly and review API latency dashboards every morning.",
                    "source_ref": "internal://eng-notes",
                }
            ],
        },
    )
    assert load_response.status_code == 200

    response = internal_data_client.post(
        "/api/internal-data/retrieve",
        json={"query": "orchid greenhouse watering schedule", "limit": 3},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_chunks_considered"] >= 1
    assert len(data["results"]) >= 1
    assert data["results"][0]["score"] < 0.6


@pytest.mark.smoke
def test_google_docs_load_returns_observable_counts(
    internal_data_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    def fake_fetch_google_docs(document_ids: list[str]) -> list[GoogleDocContent]:
        return [
            GoogleDocContent(
                document_id=document_id,
                title=f"Google Doc {index + 1}",
                content=f"Deployment details for doc {index + 1}.",
            )
            for index, document_id in enumerate(document_ids)
        ]

    monkeypatch.setattr(
        "services.internal_data_service.fetch_google_docs",
        fake_fetch_google_docs,
    )

    response = internal_data_client.post(
        "/api/internal-data/load",
        json={
            "source_type": "google_docs",
            "document_ids": ["doc-alpha", "doc-beta"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["source_type"] == "google_docs"
    assert data["documents_loaded"] == 2
    assert data["chunks_created"] >= 2

    retrieve_response = internal_data_client.post(
        "/api/internal-data/retrieve",
        json={"query": "deployment details", "limit": 3},
    )
    assert retrieve_response.status_code == 200
    retrieve_data = retrieve_response.json()
    assert any(result["source_type"] == "google_docs" for result in retrieve_data["results"])
    assert any(result["source_ref"].startswith("gdoc://") for result in retrieve_data["results"])


@pytest.mark.smoke
def test_google_docs_load_returns_controlled_error_when_token_missing(
    internal_data_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("GOOGLE_DOCS_ACCESS_TOKEN", raising=False)

    response = internal_data_client.post(
        "/api/internal-data/load",
        json={
            "source_type": "google_docs",
            "document_ids": ["doc-without-token"],
        },
    )

    assert response.status_code == 503
    assert "GOOGLE_DOCS_ACCESS_TOKEN" in response.json()["detail"]
