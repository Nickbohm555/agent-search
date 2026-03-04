import pytest


@pytest.mark.smoke
def test_mcp_tools_endpoint_exposes_runtime_agent_tool(client):
    response = client.get("/api/mcp/tools")

    assert response.status_code == 200
    payload = response.json()
    assert "tools" in payload
    assert len(payload["tools"]) == 1

    tool = payload["tools"][0]
    assert tool["name"] == "agent.run"
    assert isinstance(tool["description"], str)
    assert tool["description"].strip() != ""
    assert tool["input_schema"]["required"] == ["query"]
    assert "query" in tool["input_schema"]["properties"]


@pytest.mark.smoke
def test_mcp_invoke_delegates_to_runtime_agent_and_returns_final_answer(client):
    response = client.post(
        "/api/mcp/invoke",
        json={
            "tool_name": "agent.run",
            "arguments": {
                "query": "Summarize our internal deployment readiness checklist.",
                "thread_id": "mcp-smoke-thread",
                "user_id": "mcp-user-1",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool_name"] == "agent.run"
    assert isinstance(payload["content"], str)
    assert payload["content"].strip() != ""

    run_payload = payload["run"]
    assert run_payload["thread_id"] == "mcp-smoke-thread"
    assert isinstance(run_payload["output"], str)
    assert run_payload["output"].strip() != ""
    assert len(run_payload["sub_queries"]) >= 1
    assert len(run_payload["tool_assignments"]) == len(run_payload["sub_queries"])
