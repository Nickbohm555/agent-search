import pytest


@pytest.mark.smoke
def test_web_search_returns_link_metadata_only(client):
    response = client.post(
        "/api/web/search",
        json={"query": "latest competitor launch update", "limit": 2},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "latest competitor launch update"
    assert len(data["results"]) == 2
    for result in data["results"]:
        assert set(result.keys()) == {"title", "url", "snippet"}
        assert result["title"].strip() != ""
        assert result["url"].startswith("https://")
        assert result["snippet"].strip() != ""


@pytest.mark.smoke
def test_web_open_url_returns_full_page_content(client):
    search_response = client.post(
        "/api/web/search",
        json={"query": "competitor launch", "limit": 1},
    )
    assert search_response.status_code == 200
    top_result = search_response.json()["results"][0]

    open_response = client.post(
        "/api/web/open-url",
        json={"url": top_result["url"]},
    )
    assert open_response.status_code == 200
    data = open_response.json()
    assert data["url"] == top_result["url"]
    assert data["title"] == top_result["title"]
    assert isinstance(data["content"], str)
    assert len(data["content"].strip()) > 40


@pytest.mark.smoke
def test_agent_run_executes_search_then_open_for_web_subquery(client):
    response = client.post(
        "/api/agents/run",
        json={
            "query": "Find the latest public competitor launch update from the web.",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert any(item["tool"] == "web" for item in payload["tool_assignments"])
    assert len(payload["web_tool_runs"]) >= 1
    assert any(item["tool"] == "web" for item in payload["retrieval_results"])

    web_run = payload["web_tool_runs"][0]
    assert web_run["sub_query"].strip() != ""
    assert len(web_run["search_results"]) >= 1
    assert len(web_run["opened_urls"]) >= 1
    assert web_run["opened_urls"][0] == web_run["opened_pages"][0]["url"]
    assert len(web_run["opened_pages"][0]["content"].strip()) > 40
