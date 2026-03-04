import pytest


def _assignment_for_sub_query(assignments: list[dict], contains_text: str) -> dict:
    for assignment in assignments:
        if contains_text.lower() in assignment["sub_query"].lower():
            return assignment
    raise AssertionError(f"Expected assignment for text: {contains_text}")


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
    assert isinstance(data["tool_assignments"], list)
    assert len(data["tool_assignments"]) == len(data["sub_queries"])
    assert [item["sub_query"] for item in data["tool_assignments"]] == data["sub_queries"]
    assert all(item["tool"] in {"internal", "web"} for item in data["tool_assignments"])
    assert isinstance(data["retrieval_results"], list)
    assert len(data["retrieval_results"]) == len(data["sub_queries"])
    assert [item["sub_query"] for item in data["retrieval_results"]] == data["sub_queries"]
    assert isinstance(data["validation_results"], list)
    assert len(data["validation_results"]) == len(data["sub_queries"])
    assert [item["sub_query"] for item in data["validation_results"]] == data["sub_queries"]
    assert all(item["status"] in {"validated", "stopped_insufficient"} for item in data["validation_results"])
    assert all(item["attempts"] >= 1 for item in data["validation_results"])


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
    assert len(data["tool_assignments"]) == len(data["sub_queries"])
    assert [item["sub_query"] for item in data["tool_assignments"]] == data["sub_queries"]


@pytest.mark.smoke
def test_runtime_agent_run_assigns_tools_per_subquery(client):
    response = client.post(
        "/api/agents/run",
        json={
            "query": (
                "Summarize our internal runbook for deployment readiness; "
                "find the latest public competitor launch update."
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["tool_assignments"]) == len(data["sub_queries"])

    internal_assignment = _assignment_for_sub_query(data["tool_assignments"], "runbook")
    web_assignment = _assignment_for_sub_query(data["tool_assignments"], "competitor")

    assert internal_assignment["tool"] == "internal"
    assert web_assignment["tool"] == "web"


@pytest.mark.smoke
def test_runtime_agent_run_splits_compare_style_mixed_domain_query(client):
    response = client.post(
        "/api/agents/run",
        json={
            "query": (
                "Compare our internal release runbook with the latest public competitor launch "
                "update."
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["sub_queries"]) >= 2
    assert all(not _is_mixed_domain_prompt(sub_query) for sub_query in data["sub_queries"])
    assert len(data["tool_assignments"]) == len(data["sub_queries"])
    assert [item["sub_query"] for item in data["tool_assignments"]] == data["sub_queries"]
    assert any(item["tool"] == "internal" for item in data["tool_assignments"])
    assert any(item["tool"] == "web" for item in data["tool_assignments"])


@pytest.mark.smoke
def test_runtime_agent_run_deduplicates_duplicate_heavy_subqueries(client):
    response = client.post(
        "/api/agents/run",
        json={
            "query": (
                "Please summarize our internal runbook deployment checklist and also summarize "
                "our internal runbook deployment checklist; then find the latest public competitor "
                "launch update and find the latest public competitor launch update."
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    normalized = [sub_query.strip().lower() for sub_query in data["sub_queries"]]
    assert len(normalized) == len(set(normalized))
    assert all(sub_query for sub_query in normalized)
    assert all(not _is_mixed_domain_prompt(sub_query) for sub_query in data["sub_queries"])
    assert len(data["tool_assignments"]) == len(data["sub_queries"])
    assert [item["sub_query"] for item in data["tool_assignments"]] == data["sub_queries"]


@pytest.mark.smoke
def test_runtime_agent_run_rejects_empty_query(client):
    response = client.post("/api/agents/run", json={"query": ""})

    assert response.status_code == 422
