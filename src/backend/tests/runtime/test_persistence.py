from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest

from agent_search.errors import SDKConfigurationError
from agent_search.runtime import persistence


class _FakeResult:
    def __init__(self, schema_ready: bool) -> None:
        self._schema_ready = schema_ready

    def fetchone(self) -> dict[str, bool]:
        return {"schema_ready": self._schema_ready}


class _FakeCursor:
    def __init__(self, schema_ready: bool) -> None:
        self._schema_ready = schema_ready

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        _ = exc_type, exc, tb

    def execute(self, _query: str) -> _FakeResult:
        return _FakeResult(self._schema_ready)


class _FakeCheckpointer:
    def __init__(self, *, schema_ready: bool) -> None:
        self._schema_ready = schema_ready
        self.setup_calls = 0

    def _cursor(self) -> _FakeCursor:
        return _FakeCursor(self._schema_ready)

    def setup(self) -> None:
        self.setup_calls += 1


@pytest.fixture(autouse=True)
def clear_bootstrapped_connections() -> None:
    persistence._BOOTSTRAPPED_CONNECTIONS.clear()


def test_get_checkpointer_connection_string_requires_explicit_database_url() -> None:
    with pytest.raises(SDKConfigurationError, match="checkpoint_db_url is required"):
        persistence.get_checkpointer_connection_string(None)


def test_bootstrap_checkpointer_skips_setup_when_schema_exists() -> None:
    checkpointer = _FakeCheckpointer(schema_ready=True)

    persistence._bootstrap_checkpointer(checkpointer, connection_string="postgresql://checkpoint-db")

    assert checkpointer.setup_calls == 0


def test_bootstrap_checkpointer_runs_setup_when_schema_missing() -> None:
    checkpointer = _FakeCheckpointer(schema_ready=False)

    persistence._bootstrap_checkpointer(checkpointer, connection_string="postgresql://checkpoint-db")

    assert checkpointer.setup_calls == 1
