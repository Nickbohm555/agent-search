import pytest

from agents.langgraph_agent import get_subagents


@pytest.mark.smoke
def test_deepagent_subagent_definitions_include_required_fields_and_callable_tools():
    subagents = get_subagents()

    assert len(subagents) >= 1
    specialized = subagents[0]
    for key in ("name", "description", "system_prompt", "tools"):
        assert key in specialized

    assert specialized["name"] == "subquery-executor"
    assert isinstance(specialized["tools"], list)
    assert len(specialized["tools"]) >= 1
    assert all(callable(tool) for tool in specialized["tools"])


@pytest.mark.smoke
def test_agent_run_delegates_subqueries_via_named_subagent_task_path(client):
    response = client.post(
        "/api/agents/run",
        json={
            "query": (
                "From our internal docs summarize deployment readiness; "
                "find the latest public competitor launch update."
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    execution = payload["graph_state"]["graph"]["execution"]
    delegations = execution["delegations"]

    assert len(delegations) >= 1
    assert len(delegations) == len(payload["sub_queries"])
    assert all(item["subagent_name"] == "subquery-executor" for item in delegations)
    assert all(item["delegated_via"] == "task" for item in delegations)
    assert all(isinstance(item["summary"], str) and item["summary"].strip() for item in delegations)

    timeline = payload["graph_state"]["timeline"]
    completed_delegations = [
        item
        for item in timeline
        if item.get("step") == "subagent.delegation" and item.get("status") == "completed"
    ]
    assert len(completed_delegations) == len(payload["sub_queries"])
