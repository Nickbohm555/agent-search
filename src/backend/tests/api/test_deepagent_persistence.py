from uuid import uuid4

import pytest


@pytest.mark.smoke
def test_agent_run_same_thread_exposes_prior_checkpoint_state(client):
    thread_id = f"thread-{uuid4()}"
    user_id = f"user-{uuid4()}"
    first = client.post(
        "/api/agents/run",
        json={"query": "first persistent run", "thread_id": thread_id, "user_id": user_id},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/agents/run",
        json={"query": "second persistent run", "thread_id": thread_id, "user_id": user_id},
    )
    assert second.status_code == 200
    execution = second.json()["graph_state"]["graph"]["execution"]
    persistence = execution["persistence"]

    assert execution["thread_id"] == thread_id
    assert persistence["thread_checkpoint_count_before_run"] == 1
    assert len(persistence["thread_checkpoint_ids_before_run"]) == 1


@pytest.mark.smoke
def test_agent_run_different_thread_ids_do_not_share_checkpoint_state(client):
    user_id = f"user-{uuid4()}"
    thread_id_a = f"thread-{uuid4()}"
    thread_id_b = f"thread-{uuid4()}"

    first = client.post(
        "/api/agents/run",
        json={"query": "seed thread A", "thread_id": thread_id_a, "user_id": user_id},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/agents/run",
        json={"query": "independent thread B", "thread_id": thread_id_b, "user_id": user_id},
    )
    assert second.status_code == 200
    execution = second.json()["graph_state"]["graph"]["execution"]
    persistence = execution["persistence"]

    assert execution["thread_id"] == thread_id_b
    assert persistence["thread_checkpoint_count_before_run"] == 0
    assert persistence["thread_checkpoint_ids_before_run"] == []


@pytest.mark.smoke
def test_agent_run_with_valid_checkpoint_id_replays_without_error(client):
    thread_id = f"thread-{uuid4()}"
    user_id = f"user-{uuid4()}"
    first = client.post(
        "/api/agents/run",
        json={"query": "checkpoint source", "thread_id": thread_id, "user_id": user_id},
    )
    assert first.status_code == 200
    initial_execution = first.json()["graph_state"]["graph"]["execution"]
    resolved_checkpoint_id = initial_execution["persistence"]["resolved_checkpoint_id"]

    replay = client.post(
        "/api/agents/run",
        json={
            "query": "checkpoint replay",
            "thread_id": thread_id,
            "user_id": user_id,
            "checkpoint_id": resolved_checkpoint_id,
        },
    )
    assert replay.status_code == 200
    replay_payload = replay.json()
    replay_execution = replay_payload["graph_state"]["graph"]["execution"]
    replay_persistence = replay_execution["persistence"]

    assert replay_payload["checkpoint_id"] == resolved_checkpoint_id
    assert replay_execution["checkpoint_id"] == resolved_checkpoint_id
    assert replay_persistence["replayed_checkpoint_id"] == resolved_checkpoint_id
    assert replay_persistence["known_checkpoint"] is True


@pytest.mark.smoke
def test_agent_run_user_namespace_store_is_resolved_from_user_context(client):
    user_id = f"user-{uuid4()}"
    first_thread = f"thread-{uuid4()}"
    second_thread = f"thread-{uuid4()}"

    first = client.post(
        "/api/agents/run",
        json={"query": "store seed", "thread_id": first_thread, "user_id": user_id},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/agents/run",
        json={"query": "store reuse", "thread_id": second_thread, "user_id": user_id},
    )
    assert second.status_code == 200
    persistence = second.json()["graph_state"]["graph"]["execution"]["persistence"]

    assert persistence["store_namespace"] == [user_id, "memories"]
    assert persistence["store_entry_count_before_run"] == 1
    assert persistence["store_thread_ids_before_run"] == [first_thread]
