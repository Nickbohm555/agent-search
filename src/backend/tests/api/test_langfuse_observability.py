import pytest
from fastapi.testclient import TestClient

from main import app
from observability import langfuse as langfuse_module


class _FakeSpan:
    def __init__(self) -> None:
        self.updated = False

    def update(self, **kwargs) -> None:
        self.updated = bool(kwargs)


class _FakeSpanContextManager:
    def __enter__(self) -> _FakeSpan:
        return _FakeSpan()

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakeLangfuse:
    last_init_kwargs = None

    def __init__(self, **kwargs) -> None:
        _FakeLangfuse.last_init_kwargs = kwargs

    def start_as_current_span(self, name: str, **kwargs):
        return _FakeSpanContextManager()


@pytest.mark.smoke
def test_startup_initializes_langfuse_client_when_enabled_and_configured(monkeypatch):
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "public")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "secret")
    monkeypatch.setattr(langfuse_module, "LangfuseClient", _FakeLangfuse)

    with TestClient(app):
        handle = app.state.langfuse
        assert handle.enabled is True
        assert isinstance(handle.client, _FakeLangfuse)
        with handle.start_as_current_span(name="agent.run") as span:
            span.update(output="ok")

    assert _FakeLangfuse.last_init_kwargs is not None
    assert _FakeLangfuse.last_init_kwargs["public_key"] == "public"
    assert _FakeLangfuse.last_init_kwargs["secret_key"] == "secret"


@pytest.mark.smoke
def test_initializer_returns_disabled_handle_when_credentials_missing(monkeypatch):
    monkeypatch.setenv("LANGFUSE_ENABLED", "true")
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)

    handle = langfuse_module.initialize_langfuse_tracing()
    assert handle.enabled is False
    assert handle.client is None


@pytest.mark.smoke
def test_disabled_handle_span_creation_is_noop(monkeypatch):
    monkeypatch.setenv("LANGFUSE_ENABLED", "false")
    handle = langfuse_module.initialize_langfuse_tracing()

    with handle.start_as_current_span(name="disabled-trace") as span:
        span.update(output="ignored")

    assert handle.enabled is False
