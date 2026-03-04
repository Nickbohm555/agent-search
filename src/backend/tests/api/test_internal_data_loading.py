import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db import Base, get_db
from main import app


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
