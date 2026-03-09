from __future__ import annotations

import sys
import types
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from config import LangfuseSettings
from utils import langfuse_tracing


def test_build_langfuse_callback_handler_returns_none_when_disabled(monkeypatch) -> None:
    settings = LangfuseSettings(enabled=False)
    handler = langfuse_tracing.build_langfuse_callback_handler(settings=settings)
    assert handler is None


def test_build_langfuse_callback_handler_returns_none_when_keys_missing(monkeypatch) -> None:
    settings = LangfuseSettings(enabled=True, public_key="", secret_key="")
    handler = langfuse_tracing.build_langfuse_callback_handler(settings=settings)
    assert handler is None


def test_build_langfuse_callback_handler_builds_from_settings(monkeypatch) -> None:
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

    settings = LangfuseSettings(
        enabled=True,
        public_key="pk_test",
        secret_key="sk_test",
        host="https://cloud.langfuse.com",
        environment="test",
        release="1.2.3",
        runtime_sample_rate=1.0,
    )

    langfuse_tracing.get_langfuse_client(settings=settings, force_reinit=True)
    handler = langfuse_tracing.build_langfuse_callback_handler(settings=settings)

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


def test_build_langfuse_callback_handler_applies_scope_sampling(monkeypatch) -> None:
    class _FakeLangfuseClient:
        def __init__(self, **kwargs):
            pass

    class _FakeCallbackHandler:
        def __init__(self, **kwargs):
            pass

    fake_module = types.SimpleNamespace(CallbackHandler=_FakeCallbackHandler)
    fake_langfuse_module = types.SimpleNamespace(Langfuse=_FakeLangfuseClient)
    monkeypatch.setitem(sys.modules, "langfuse", fake_langfuse_module)
    monkeypatch.setitem(sys.modules, "langfuse.langchain", fake_module)

    settings = LangfuseSettings(
        enabled=True,
        public_key="pk_test",
        secret_key="sk_test",
        runtime_sample_rate=0.0,
        benchmark_sample_rate=1.0,
    )

    runtime_handler = langfuse_tracing.build_langfuse_callback_handler(
        settings=settings,
        scope="runtime",
        sampling_key="run-1",
    )
    benchmark_handler = langfuse_tracing.build_langfuse_callback_handler(
        settings=settings,
        scope="benchmark",
        sampling_key="run-1",
    )

    assert runtime_handler is None
    assert isinstance(benchmark_handler, _FakeCallbackHandler)


def test_get_langfuse_client_returns_none_when_disabled() -> None:
    settings = LangfuseSettings(enabled=False)
    client = langfuse_tracing.get_langfuse_client(settings=settings, force_reinit=True)
    assert client is None


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
