import pytest


@pytest.mark.smoke
def test_mcp_tools_list_exposes_stable_agent_run_contract(client):
    initialize_response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert initialize_response.status_code == 200
    initialize_payload = initialize_response.json()
    assert initialize_payload["jsonrpc"] == "2.0"
    assert initialize_payload["id"] == 1
    assert initialize_payload["result"]["protocolVersion"] == "2024-11-05"
    assert initialize_payload["result"]["serverInfo"] == {
        "name": "agent-search-mcp",
        "version": "0.1.0",
    }

    list_response = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["jsonrpc"] == "2.0"
    assert list_payload["id"] == 2
    assert list_payload["result"]["tools"] == [
        {
            "name": "agent.run",
            "description": "Run the orchestrated query pipeline and return a synthesized answer.",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string", "minLength": 1}},
                "required": ["query"],
                "additionalProperties": False,
            },
        }
    ]


@pytest.mark.smoke
def test_mcp_tools_call_delegates_to_runtime_agent_orchestration(client):
    query = "Compare our internal runbook notes with the latest public competitor launch update."

    api_response = client.post("/api/agents/run", json={"query": query})
    assert api_response.status_code == 200
    api_payload = api_response.json()

    mcp_response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "agent.run", "arguments": {"query": query}},
        },
    )
    assert mcp_response.status_code == 200
    mcp_payload = mcp_response.json()

    assert mcp_payload["jsonrpc"] == "2.0"
    assert mcp_payload["id"] == 3
    assert mcp_payload["result"]["isError"] is False
    assert mcp_payload["result"]["content"] == [{"type": "text", "text": api_payload["output"]}]
    assert mcp_payload["result"]["structuredContent"] == api_payload
    assert isinstance(api_payload["subquery_execution_results"], list)
    assert "attempt_trace" in api_payload["subquery_execution_results"][0]["validation_result"]


@pytest.mark.smoke
def test_fastmcp_streamable_http_tooling_is_reachable_and_invocable(client):
    initialize_response = client.post(
        "/mcp/fast/mcp/",
        headers={"accept": "application/json, text/event-stream"},
        json={
            "jsonrpc": "2.0",
            "id": "init-1",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pytest-client", "version": "0.1.0"},
            },
        },
    )
    assert initialize_response.status_code == 200
    initialize_payload = initialize_response.json()
    assert initialize_payload["jsonrpc"] == "2.0"
    assert initialize_payload["id"] == "init-1"
    assert "result" in initialize_payload

    tools_response = client.post(
        "/mcp/fast/mcp/",
        headers={"accept": "application/json, text/event-stream"},
        json={"jsonrpc": "2.0", "id": "list-1", "method": "tools/list", "params": {}},
    )
    assert tools_response.status_code == 200
    tools_payload = tools_response.json()
    assert tools_payload["jsonrpc"] == "2.0"
    assert tools_payload["id"] == "list-1"
    tools = tools_payload["result"]["tools"]
    assert any(tool["name"] == "agent.run" for tool in tools)

    call_response = client.post(
        "/mcp/fast/mcp/",
        headers={"accept": "application/json, text/event-stream"},
        json={
            "jsonrpc": "2.0",
            "id": "call-1",
            "method": "tools/call",
            "params": {"name": "agent.run", "arguments": {"query": "Summarize latest run."}},
        },
    )
    assert call_response.status_code == 200
    call_payload = call_response.json()
    assert call_payload["jsonrpc"] == "2.0"
    assert call_payload["id"] == "call-1"
    assert "result" in call_payload
