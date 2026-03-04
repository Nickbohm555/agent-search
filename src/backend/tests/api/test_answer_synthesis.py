import pytest


@pytest.mark.smoke
def test_agent_run_synthesizes_single_answer_from_validated_results(client):
    marker = "synthesis-marker-9n"
    load_response = client.post(
        "/api/internal-data/load",
        json={
            "source_type": "inline",
            "documents": [
                {
                    "title": "Customer Escalation Playbook",
                    "content": (
                        "The customer escalation process requires incident commander paging. "
                        f"Key token: {marker}."
                    ),
                    "source_ref": "internal://escalation-playbook",
                }
            ],
        },
    )
    assert load_response.status_code == 200

    query = f"From our internal docs, summarize the escalation process and include {marker}."
    response = client.post("/api/agents/run", json={"query": query})
    assert response.status_code == 200

    payload = response.json()
    assert isinstance(payload["output"], str)
    assert payload["output"].strip() != ""
    assert query in payload["output"]
    assert marker in payload["output"]


@pytest.mark.smoke
def test_synthesis_uses_only_validated_subquery_outputs(client):
    query = (
        "From our internal docs summarize the nonexistent codename omega-void; "
        "find the latest public competitor launch update."
    )
    response = client.post("/api/agents/run", json={"query": query})
    assert response.status_code == 200

    payload = response.json()
    assert len(payload["validation_results"]) == 2
    assert payload["validation_results"][0]["status"] == "stopped_insufficient"
    assert payload["validation_results"][1]["status"] == "validated"

    answer = payload["output"]
    assert "Insufficient validated evidence for sub-query:" in answer
    assert "Competitor Z confirmed a Spring 2026 rollout" in answer
