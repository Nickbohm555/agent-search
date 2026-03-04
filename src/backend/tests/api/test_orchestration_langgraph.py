import pytest


def _step_indexes(timeline: list[dict], step: str, status: str) -> list[int]:
    return [
        idx
        for idx, item in enumerate(timeline)
        if item.get("step") == step and item.get("status") == status
    ]


@pytest.mark.smoke
def test_agent_run_exposes_deepagent_runtime_execution_metadata(client):
    """Orchestration uses DeepAgent library only; no LangGraph/StateGraph."""
    response = client.post("/api/agents/run", json={"query": "hello orchestration"})

    assert response.status_code == 200
    payload = response.json()
    graph_state = payload["graph_state"]
    assert graph_state["current_step"] == "completed"
    assert graph_state["graph"]["kind"] == "deepagent-runtime"
    assert graph_state["graph"]["runtime"]["library"] == "deepagent"
    assert graph_state["graph"]["execution"]["execution_id"] != ""
    assert graph_state["graph"]["execution"]["subquery_execution_count"] == len(
        payload["sub_queries"]
    )
    deep_agents = graph_state["graph"]["deep_agents"]
    assert len(deep_agents) == 1
    assert deep_agents[0]["name"] == "subquery_execution_agent"
    assert "retrieval" in deep_agents[0]["nodes"]
    assert "validation" in deep_agents[0]["nodes"]


@pytest.mark.smoke
def test_agent_run_deepagent_enforces_pipeline_order_and_per_subquery_validation_loop(client):
    response = client.post(
        "/api/agents/run",
        json={
            "query": (
                "From our internal docs summarize the nonexistent codename omega-void; "
                "find the latest public competitor launch update."
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    timeline = payload["graph_state"]["timeline"]
    decomposition_completed = _step_indexes(timeline, "decomposition", "completed")
    tool_selection_completed = _step_indexes(timeline, "tool_selection", "completed")
    retrieval_completed = _step_indexes(timeline, "subquery_execution.retrieval", "completed")
    validation_completed = _step_indexes(timeline, "subquery_execution.validation", "completed")
    synthesis_completed = _step_indexes(timeline, "synthesis", "completed")

    assert decomposition_completed
    assert tool_selection_completed
    assert retrieval_completed
    assert validation_completed
    assert synthesis_completed
    assert decomposition_completed[0] < tool_selection_completed[0]
    assert tool_selection_completed[0] < retrieval_completed[0]
    assert retrieval_completed[-1] < synthesis_completed[0]
    assert len(retrieval_completed) == len(payload["sub_queries"])
    assert len(validation_completed) == len(payload["sub_queries"])

    internal_validations = [
        item for item in payload["validation_results"] if item["tool"] == "internal"
    ]
    assert internal_validations
    assert internal_validations[0]["attempts"] == 2
    assert internal_validations[0]["status"] == "stopped_insufficient"
