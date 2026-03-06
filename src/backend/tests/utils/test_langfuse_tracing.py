from __future__ import annotations

import sys
import types
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from utils import langfuse_tracing


def test_build_langfuse_callback_handler_returns_none_when_disabled(monkeypatch) -> None:
    monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)
    assert langfuse_tracing.build_langfuse_callback_handler() is None


def test_build_langfuse_callback_handler_returns_none_when_keys_missing(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    assert langfuse_tracing.build_langfuse_callback_handler() is None


def test_build_langfuse_callback_handler_builds_from_env(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeLangfuseClient:
        def __init__(self, **kwargs):
            captured["client_kwargs"] = kwargs

    class _FakeCallbackHandler:
        def __init__(self, *, public_key=None, secret_key=None, host=None, environment=None, release=None):
            captured["kwargs"] = {
                "public_key": public_key,
                "secret_key": secret_key,
                "host": host,
                "environment": environment,
                "release": release,
            }

    fake_module = types.SimpleNamespace(CallbackHandler=_FakeCallbackHandler)
    fake_langfuse_module = types.SimpleNamespace(Langfuse=_FakeLangfuseClient)
    monkeypatch.setitem(sys.modules, "langfuse", fake_langfuse_module)
    monkeypatch.setitem(sys.modules, "langfuse.langchain", fake_module)

    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk_test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk_test")
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)
    monkeypatch.setenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    monkeypatch.setenv("LANGFUSE_ENVIRONMENT", "test")
    monkeypatch.setenv("LANGFUSE_RELEASE", "1.2.3")

    handler = langfuse_tracing.build_langfuse_callback_handler()

    assert isinstance(handler, _FakeCallbackHandler)
    assert captured["client_kwargs"] == {
        "public_key": "pk_test",
        "secret_key": "sk_test",
        "tracing_enabled": True,
        "host": "https://cloud.langfuse.com",
        "environment": "test",
        "release": "1.2.3",
    }
    assert captured["kwargs"] == {
        "public_key": "pk_test",
        "secret_key": "sk_test",
        "host": "https://cloud.langfuse.com",
        "environment": "test",
        "release": "1.2.3",
    }


def test_flush_langfuse_callback_handler_uses_handler_flush() -> None:
    state = {"flushed": False}

    class _Handler:
        def flush(self) -> None:
            state["flushed"] = True

    langfuse_tracing.flush_langfuse_callback_handler(_Handler())
    assert state["flushed"] is True


def test_flush_langfuse_callback_handler_uses_client_flush() -> None:
    state = {"flushed": False}

    class _Client:
        def flush(self) -> None:
            state["flushed"] = True

    class _Handler:
        langfuse = _Client()

    langfuse_tracing.flush_langfuse_callback_handler(_Handler())
    assert state["flushed"] is True
