from uuid import uuid4

import pytest


def _step_indexes(timeline: list[dict], step: str, status: str) -> list[int]:
    return [
        idx
        for idx, item in enumerate(timeline)
        if item.get("step") == step and item.get("status") == status
    ]


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


@pytest.mark.smoke
def test_agent_run_memory_reads_are_user_scoped_and_retrieved_on_later_run(client):
    user_a = f"user-{uuid4()}"
    user_b = f"user-{uuid4()}"
    thread_a = f"thread-{uuid4()}"
    thread_b = f"thread-{uuid4()}"
    query = "remember this deterministic preference"

    first_a = client.post(
        "/api/agents/run",
        json={"query": query, "thread_id": thread_a, "user_id": user_a},
    )
    assert first_a.status_code == 200

    second_a = client.post(
        "/api/agents/run",
        json={"query": query, "thread_id": f"thread-{uuid4()}", "user_id": user_a},
    )
    assert second_a.status_code == 200
    persistence_a = second_a.json()["graph_state"]["graph"]["execution"]["persistence"]
    read_memories_a = persistence_a["memory_reads_before_run"]
    assert len(read_memories_a) >= 1
    assert read_memories_a[0]["value"]["query"] == query
    assert read_memories_a[0]["value"]["kind"] == "final_answer_summary"

    first_b = client.post(
        "/api/agents/run",
        json={"query": query, "thread_id": thread_b, "user_id": user_b},
    )
    assert first_b.status_code == 200
    persistence_b = first_b.json()["graph_state"]["graph"]["execution"]["persistence"]
    assert persistence_b["memory_reads_before_run"] == []


@pytest.mark.smoke
def test_agent_run_memory_timeline_events_and_payload_are_deterministic(client):
    user_id = f"user-{uuid4()}"
    query = "deterministic memory payload check"
    first_thread = f"thread-{uuid4()}"
    second_thread = f"thread-{uuid4()}"

    first = client.post(
        "/api/agents/run",
        json={"query": query, "thread_id": first_thread, "user_id": user_id},
    )
    assert first.status_code == 200
    first_persistence = first.json()["graph_state"]["graph"]["execution"]["persistence"]
    first_memory_write = first_persistence["memory_write_after_synthesis"]

    second = client.post(
        "/api/agents/run",
        json={"query": query, "thread_id": second_thread, "user_id": user_id},
    )
    assert second.status_code == 200
    second_payload = second.json()
    second_persistence = second_payload["graph_state"]["graph"]["execution"]["persistence"]
    second_memory_write = second_persistence["memory_write_after_synthesis"]
    second_timeline = second_payload["graph_state"]["timeline"]

    memory_read_completed = _step_indexes(second_timeline, "memory.read", "completed")
    synthesis_completed = _step_indexes(second_timeline, "synthesis", "completed")
    memory_write_completed = _step_indexes(second_timeline, "memory.write", "completed")
    assert memory_read_completed and synthesis_completed and memory_write_completed
    assert memory_read_completed[0] < synthesis_completed[0]
    assert synthesis_completed[0] < memory_write_completed[0]

    assert first_memory_write["value"] == second_memory_write["value"]
    assert first_memory_write["memory_id"] == second_memory_write["memory_id"]
