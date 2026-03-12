from .config import RuntimeConfig, RuntimeRerankConfig, RuntimeRetrievalConfig, RuntimeTimeoutConfig
from .errors import (
    SDKConfigurationError,
    SDKError,
    SDKModelError,
    SDKRetrievalError,
    SDKTimeoutError,
)

__all__ = [
    "advanced_rag",
    "build_langfuse_callback",
    "run",
    "run_async",
    "get_run_status",
    "cancel_run",
    "RuntimeConfig",
    "RuntimeTimeoutConfig",
    "RuntimeRetrievalConfig",
    "RuntimeRerankConfig",
    "SDKError",
    "SDKConfigurationError",
    "SDKRetrievalError",
    "SDKModelError",
    "SDKTimeoutError",
]


def __getattr__(name: str):
    if name in {"advanced_rag", "build_langfuse_callback", "cancel_run", "get_run_status", "run", "run_async"}:
        from . import public_api

        return getattr(public_api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
