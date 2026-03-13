from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import threading
from typing import Any

from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.engine import make_url

from db import DATABASE_URL

_BOOTSTRAP_LOCK = threading.Lock()
_BOOTSTRAPPED_CONNECTIONS: set[str] = set()


def get_checkpointer_connection_string(database_url: str | None = None) -> str:
    raw_url = (database_url or DATABASE_URL).strip()
    normalized_url = make_url(raw_url)
    drivername = normalized_url.drivername.split("+", 1)[0]
    return normalized_url.set(drivername=drivername).render_as_string(hide_password=False)


def _bootstrap_checkpointer(checkpointer: PostgresSaver, *, connection_string: str) -> None:
    if connection_string in _BOOTSTRAPPED_CONNECTIONS:
        return
    with _BOOTSTRAP_LOCK:
        if connection_string in _BOOTSTRAPPED_CONNECTIONS:
            return
        checkpointer.setup()
        _BOOTSTRAPPED_CONNECTIONS.add(connection_string)


@contextmanager
def ready_checkpointer(
    *,
    database_url: str | None = None,
    pipeline: bool = False,
) -> Iterator[PostgresSaver]:
    connection_string = get_checkpointer_connection_string(database_url)
    with PostgresSaver.from_conn_string(connection_string, pipeline=pipeline) as checkpointer:
        _bootstrap_checkpointer(checkpointer, connection_string=connection_string)
        yield checkpointer


def ensure_checkpointer_bootstrap(*, database_url: str | None = None, pipeline: bool = False) -> None:
    with ready_checkpointer(database_url=database_url, pipeline=pipeline):
        return None


@contextmanager
def compile_graph_with_checkpointer(
    graph_builder: Any,
    *,
    database_url: str | None = None,
    pipeline: bool = False,
    **compile_kwargs: Any,
) -> Iterator[Any]:
    with ready_checkpointer(database_url=database_url, pipeline=pipeline) as checkpointer:
        yield graph_builder.compile(checkpointer=checkpointer, **compile_kwargs)


__all__ = [
    "compile_graph_with_checkpointer",
    "ensure_checkpointer_bootstrap",
    "get_checkpointer_connection_string",
    "ready_checkpointer",
]
