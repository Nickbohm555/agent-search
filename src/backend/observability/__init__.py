"""Observability scaffolding package."""

from .langfuse import LangfuseConfig, initialize_langfuse_tracing

__all__ = ["LangfuseConfig", "initialize_langfuse_tracing"]
