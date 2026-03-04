import pytest

from services.runtime_service import initialize_runtime_handle


@pytest.mark.smoke
def test_runtime_enabled_stub_mode_executes_langchain_boundary(client, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_RUNTIME_MODE", "stub")
    client.app.state.runtime_model = initialize_runtime_handle()

    response = client.post("/api/agents/run", json={"query": "runtime boundary check"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["graph_state"]["graph"]["runtime_mode"] == "enabled_stub"
    assert payload["output"].startswith("Stub runtime answer for: runtime boundary check")


@pytest.mark.smoke
def test_runtime_missing_provider_config_falls_back_without_crash(client, monkeypatch):
    monkeypatch.setenv("AGENT_RUNTIME_ENABLED", "true")
    monkeypatch.setenv("AGENT_RUNTIME_MODE", "langchain_openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client.app.state.runtime_model = initialize_runtime_handle()

    response = client.post("/api/agents/run", json={"query": "no key should fallback"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["graph_state"]["graph"]["runtime_mode"] == "missing_openai_config"
    assert payload["output"].startswith("Final answer for query: no key should fallback")
