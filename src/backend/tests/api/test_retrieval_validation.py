import pytest


def _find_validation_result(results: list[dict], tool: str) -> dict:
    for result in results:
        if result["tool"] == tool:
            return result
    raise AssertionError(f"Expected validation result for tool={tool}")


@pytest.mark.smoke
def test_agent_run_marks_internal_retrieval_as_validated_when_results_exist(client):
    marker = "validation-marker-7q"
    load_response = client.post(
        "/api/internal-data/load",
        json={
            "source_type": "inline",
            "documents": [
                {
                    "title": "Validation Notes",
                    "content": f"The notes include {marker} for deterministic validation checks.",
                    "source_ref": "internal://validation-notes",
                }
            ],
        },
    )
    assert load_response.status_code == 200

    response = client.post("/api/agents/run", json={"query": f"From our internal docs find {marker}."})
    assert response.status_code == 200

    payload = response.json()
    validation = _find_validation_result(payload["validation_results"], "internal")
    assert validation["sufficient"] is True
    assert validation["status"] == "validated"
    assert validation["attempts"] == 1
    assert validation["follow_up_actions"] == []
    assert validation["stop_reason"] == "sufficient_evidence"


@pytest.mark.smoke
def test_agent_run_retries_internal_retrieval_then_stops_when_insufficient(client):
    response = client.post(
        "/api/agents/run",
        json={"query": "From our internal docs summarize the nonexistent launch codename omega-void."},
    )
    assert response.status_code == 200

    payload = response.json()
    validation = _find_validation_result(payload["validation_results"], "internal")
    assert validation["sufficient"] is False
    assert validation["status"] == "stopped_insufficient"
    assert validation["attempts"] == 2
    assert validation["follow_up_actions"] == ["search_more_internal"]
    assert validation["stop_reason"] == "max_attempts_reached"
