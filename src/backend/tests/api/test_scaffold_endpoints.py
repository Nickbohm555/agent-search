import pytest


def _is_mixed_domain_prompt(text: str) -> bool:
    lowered = text.lower()
    has_internal = any(
        token in lowered
        for token in (
            "internal",
            "docs",
            "documentation",
            "knowledge base",
            "repository",
            "our",
        )
    )
    has_web = any(
        token in lowered
        for token in (
            "web",
            "internet",
            "online",
            "latest",
            "news",
            "today",
            "public",
            "external",
            "website",
            "competitor",
        )
    )
    return has_internal and has_web


@pytest.mark.smoke
def test_search_skeleton_endpoint(client):
    response = client.get("/api/search-skeleton")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "scaffold"
    assert isinstance(data["message"], str)
    assert data["message"].strip() != ""


@pytest.mark.smoke
def test_runtime_agent_info_endpoint(client):
    response = client.get("/api/agents/runtime")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["name"], str)
    assert data["name"].strip() != ""
    assert isinstance(data["version"], str)
    assert data["version"].strip() != ""


@pytest.mark.smoke
def test_runtime_agent_run_endpoint(client):
    response = client.post("/api/agents/run", json={"query": "hello"})

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["agent_name"], str)
    assert data["agent_name"].strip() != ""
    assert isinstance(data["output"], str)
    assert data["output"].strip() != ""
    assert isinstance(data["sub_queries"], list)
    assert len(data["sub_queries"]) >= 1
    assert all(isinstance(sub_query, str) and sub_query.strip() for sub_query in data["sub_queries"])


@pytest.mark.smoke
def test_runtime_agent_run_decomposes_complex_query_without_mixed_domain_subqueries(client):
    response = client.post(
        "/api/agents/run",
        json={
            "query": (
                "From our internal docs summarize the Q4 launch checklist and "
                "find the latest public competitor announcement."
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["sub_queries"]) >= 2
    assert all(not _is_mixed_domain_prompt(sub_query) for sub_query in data["sub_queries"])


@pytest.mark.smoke
def test_runtime_agent_run_rejects_empty_query(client):
    response = client.post("/api/agents/run", json={"query": ""})

    assert response.status_code == 422
