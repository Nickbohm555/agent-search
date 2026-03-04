import pytest


@pytest.mark.smoke
def test_agent_run_query_only_payload_generates_thread_id(client):
    response = client.post("/api/agents/run", json={"query": "hello config contract"})

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["thread_id"], str)
    assert payload["thread_id"].strip() != ""
    assert payload["checkpoint_id"] is None

    execution = payload["graph_state"]["graph"]["execution"]
    assert execution["thread_id"] == payload["thread_id"]
    assert execution["checkpoint_id"] is None
    assert execution["configurable"]["thread_id"] == payload["thread_id"]
    assert "checkpoint_id" not in execution["configurable"]


@pytest.mark.smoke
def test_agent_run_accepts_and_preserves_provided_persistence_config(client):
    run_config = {
        "query": "hello with explicit config",
        "thread_id": "thread-abc-123",
        "user_id": "user-42",
        "checkpoint_id": "checkpoint-99",
    }
    response = client.post("/api/agents/run", json=run_config)

    assert response.status_code == 200
    payload = response.json()
    assert payload["thread_id"] == run_config["thread_id"]
    assert payload["checkpoint_id"] == run_config["checkpoint_id"]

    execution = payload["graph_state"]["graph"]["execution"]
    assert execution["thread_id"] == run_config["thread_id"]
    assert execution["checkpoint_id"] == run_config["checkpoint_id"]
    assert execution["user_id"] == run_config["user_id"]
    assert execution["configurable"]["thread_id"] == run_config["thread_id"]
    assert execution["configurable"]["checkpoint_id"] == run_config["checkpoint_id"]
    assert execution["context"]["user_id"] == run_config["user_id"]
