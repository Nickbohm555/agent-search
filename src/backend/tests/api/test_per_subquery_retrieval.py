import pytest


def _find_retrieval_result(results: list[dict], tool: str) -> dict:
    for result in results:
        if result["tool"] == tool:
            return result
    raise AssertionError(f"Expected retrieval result for tool={tool}")


@pytest.mark.smoke
def test_agent_run_executes_internal_retrieval_from_loaded_store(client):
    marker = "retrieval-marker-42z"
    load_response = client.post(
        "/api/internal-data/load",
        json={
            "source_type": "inline",
            "documents": [
                {
                    "title": "Deployment Runbook",
                    "content": f"The internal runbook includes {marker} and rollback checklists.",
                    "source_ref": "internal://deployment-runbook",
                },
                {
                    "title": "Team Charter",
                    "content": "The team charter covers staffing and planning cadences.",
                    "source_ref": "internal://team-charter",
                },
            ],
        },
    )
    assert load_response.status_code == 200

    response = client.post(
        "/api/agents/run",
        json={"query": f"From our internal docs summarize {marker}."},
    )

    assert response.status_code == 200
    payload = response.json()
    internal_result = _find_retrieval_result(payload["retrieval_results"], "internal")
    assert len(internal_result["internal_results"]) >= 1
    assert all(item["source_type"] == "inline" for item in internal_result["internal_results"])
    assert any(marker in item["content"] for item in internal_result["internal_results"])


@pytest.mark.smoke
def test_agent_run_executes_web_retrieval_via_search_then_open(client):
    response = client.post(
        "/api/agents/run",
        json={"query": "Find the latest public competitor launch update from the web."},
    )

    assert response.status_code == 200
    payload = response.json()
    web_result = _find_retrieval_result(payload["retrieval_results"], "web")
    assert len(web_result["web_search_results"]) >= 1
    assert len(web_result["opened_urls"]) >= 1
    assert web_result["opened_urls"][0] == web_result["opened_pages"][0]["url"]
    assert len(web_result["opened_pages"][0]["content"].strip()) > 40
