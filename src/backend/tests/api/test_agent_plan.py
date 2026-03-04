import pytest


@pytest.mark.smoke
def test_agent_plan_returns_subqueries_with_one_tool(client):
    payload = {
        "query": "Summarize our internal roadmap for Q2 and list the latest public OpenAI API release notes",
    }

    response = client.post("/api/agent/plan", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == payload["query"]
    assert len(body["subqueries"]) >= 2
    assert body["trajectory"] == ["decomposition", "tool_selection"]

    allowed_tools = {"internal_rag", "web_search"}
    for subquery in body["subqueries"]:
        assert isinstance(subquery["text"], str) and subquery["text"].strip()
        assert subquery["tool"] in allowed_tools

    assert {subquery["tool"] for subquery in body["subqueries"]} == {"internal_rag", "web_search"}
    assert {event["step"] for event in body["events"]} == {"decomposition", "tool_selection"}
