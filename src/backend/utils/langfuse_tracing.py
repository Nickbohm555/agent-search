from __future__ import annotations

import logging
import os
import inspect
from typing import Any

logger = logging.getLogger(__name__)


def _is_enabled(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_langfuse_callback_handler() -> Any | None:
    """Create a Langfuse LangChain callback handler when env-based tracing is enabled."""
    enabled = _is_enabled(os.getenv("LANGFUSE_ENABLED"))
    if not enabled:
        logger.info("Langfuse tracing disabled LANGFUSE_ENABLED=%s", os.getenv("LANGFUSE_ENABLED", ""))
        return None

    public_key = (os.getenv("LANGFUSE_PUBLIC_KEY") or "").strip()
    secret_key = (os.getenv("LANGFUSE_SECRET_KEY") or "").strip()
    host = (os.getenv("LANGFUSE_BASE_URL") or os.getenv("LANGFUSE_HOST") or "").strip()
    environment = (os.getenv("LANGFUSE_ENVIRONMENT") or "").strip()
    release = (os.getenv("LANGFUSE_RELEASE") or "").strip()

    if not public_key or not secret_key:
        logger.warning(
            "Langfuse tracing enabled but credentials are missing public_key_set=%s secret_key_set=%s",
            bool(public_key),
            bool(secret_key),
        )
        return None

    try:
        from langfuse.langchain import CallbackHandler
    except Exception:  # pragma: no cover - import path can vary by SDK version.
        try:
            from langfuse.callback import CallbackHandler  # type: ignore[attr-defined]
        except Exception:
            logger.exception("Langfuse tracing enabled but callback handler import failed")
            return None

    langfuse_client: Any | None = None
    try:
        from langfuse import Langfuse

        client_kwargs: dict[str, Any] = {
            "public_key": public_key,
            "secret_key": secret_key,
            "tracing_enabled": True,
        }
        if host:
            client_kwargs["host"] = host
        if environment:
            client_kwargs["environment"] = environment
        if release:
            client_kwargs["release"] = release
        langfuse_client = Langfuse(**client_kwargs)
    except Exception:
        logger.exception("Langfuse tracing enabled but Langfuse client init failed")
        return None

    signature = inspect.signature(CallbackHandler.__init__)
    accepted = set(signature.parameters.keys()) - {"self"}
    kwargs: dict[str, Any] = {}
    if "public_key" in accepted:
        kwargs["public_key"] = public_key
    if "secret_key" in accepted:
        kwargs["secret_key"] = secret_key
    if "langfuse_public_key" in accepted:
        kwargs["langfuse_public_key"] = public_key
    if "langfuse_secret_key" in accepted:
        kwargs["langfuse_secret_key"] = secret_key
    if host:
        if "host" in accepted:
            kwargs["host"] = host
        elif "base_url" in accepted:
            kwargs["base_url"] = host
    if environment and "environment" in accepted:
        kwargs["environment"] = environment
    if release and "release" in accepted:
        kwargs["release"] = release

    try:
        handler = CallbackHandler(**kwargs)
    except Exception:
        logger.exception("Failed to initialize Langfuse callback handler")
        return None
    setattr(handler, "_agent_search_langfuse_client", langfuse_client)

    logger.info(
        "Langfuse tracing enabled host=%s environment=%s release=%s",
        host or "default",
        environment or "default",
        release or "default",
    )
    return handler


def flush_langfuse_callback_handler(handler: Any | None) -> None:
    """Best-effort flush so traces are quickly available for external harness reads."""
    if handler is None:
        return
    try:
        flush = getattr(handler, "flush", None)
        if callable(flush):
            flush()
            logger.info("Langfuse callback flush completed via handler.flush()")
            return
        client = getattr(handler, "langfuse", None)
        client_flush = getattr(client, "flush", None)
        if callable(client_flush):
            client_flush()
            logger.info("Langfuse callback flush completed via handler.langfuse.flush()")
            return
        attached_client = getattr(handler, "_agent_search_langfuse_client", None)
        attached_client_flush = getattr(attached_client, "flush", None)
        if callable(attached_client_flush):
            attached_client_flush()
            logger.info("Langfuse callback flush completed via attached Langfuse client")
            return
        logger.info("Langfuse callback flush skipped; no flush method found")
    except Exception:
        logger.exception("Langfuse callback flush failed")
