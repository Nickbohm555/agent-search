import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from main import app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_route_inventory_snapshot() -> None:
    expected_paths = {
        "/api/health",
        "/api/agents/run",
        "/api/agents/run-async",
        "/api/agents/run-status/{job_id}",
        "/api/agents/run-cancel/{job_id}",
        "/api/benchmarks/runs",
        "/api/benchmarks/runs/{run_id}",
        "/api/benchmarks/runs/{run_id}/cancel",
        "/api/benchmarks/runs/{run_id}/compare",
        "/api/benchmarks/wipe",
        "/api/internal-data/load",
        "/api/internal-data/load-async",
        "/api/internal-data/load-status/{job_id}",
        "/api/internal-data/load-cancel/{job_id}",
        "/api/internal-data/wipe",
        "/api/internal-data/wiki-sources",
    }
    openapi_paths = set(app.openapi()["paths"].keys())
    assert openapi_paths == expected_paths


def test_api_response_schema_snapshot() -> None:
    openapi = app.openapi()
    paths = openapi["paths"]

    assert paths["/api/agents/run"]["post"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/RuntimeAgentRunResponse"
    }
    assert paths["/api/agents/run-async"]["post"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/RuntimeAgentRunAsyncStartResponse"}
    assert paths["/api/agents/run-status/{job_id}"]["get"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/RuntimeAgentRunAsyncStatusResponse"}
    assert paths["/api/agents/run-cancel/{job_id}"]["post"]["responses"]["200"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/RuntimeAgentRunAsyncCancelResponse"}
    assert paths["/api/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"] == {
        "additionalProperties": {"type": "string"},
        "type": "object",
        "title": "Response Health Api Health Get",
    }
