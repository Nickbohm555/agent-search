import pytest


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


@pytest.mark.smoke
def test_runtime_agent_run_rejects_empty_query(client):
    response = client.post("/api/agents/run", json={"query": ""})

    assert response.status_code == 422
