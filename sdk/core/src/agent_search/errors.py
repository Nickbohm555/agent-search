from __future__ import annotations


class SDKError(Exception):
    """Base exception for consumer-facing SDK failures."""


class SDKConfigurationError(SDKError):
    """Raised when SDK inputs or runtime configuration are invalid."""


class SDKRetrievalError(SDKError):
    """Raised when retrieval/vector-store operations fail."""


class SDKModelError(SDKError):
    """Raised when model invocation or model configuration fails."""


class SDKTimeoutError(SDKError):
    """Raised when an SDK operation exceeds its time budget."""
