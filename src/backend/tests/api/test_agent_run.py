import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db import get_db
from routers.agent import router as agent_router


def test_post_run_returns_output_from_runtime_agent(monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    from schemas import RuntimeAgentRunResponse
    from routers import agent as agent_router_module

    captured: dict[str, object] = {}

    def fake_run_runtime_agent(payload, db):
        captured["query"] = payload.query
        assert isinstance(db, Session)
        return RuntimeAgentRunResponse(output=f"Echo: {payload.query}")

    monkeypatch.setattr(agent_router_module, "run_runtime_agent", fake_run_runtime_agent)

    app = FastAPI()
    app.include_router(agent_router)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.post("/api/agents/run", json={"query": "Find Hormuz risks"})
    assert response.status_code == 200
    assert response.json() == {"output": "Echo: Find Hormuz risks"}
    assert captured["query"] == "Find Hormuz risks"
