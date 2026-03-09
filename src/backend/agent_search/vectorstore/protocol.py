from __future__ import annotations

import inspect
import logging
from typing import Any, Protocol, cast, runtime_checkable

from agent_search.errors import SDKConfigurationError
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """Required vector-store contract for SDK retrieval integration.

    Semantics:
    - Must return at most `k` LangChain `Document` objects sorted by descending
      relevance for `query`.
    - `filter` is optional and, when provided, should constrain retrieval.
    - Implementations may expose score-returning APIs in addition to this base
      contract, but `similarity_search` is mandatory.
    """

    def similarity_search(
        self,
        query: str,
        k: int,
        filter: dict[str, Any] | None = None,
    ) -> list[Document]:
        """Return top-k documents for the query."""


def assert_vector_store_compatible(vector_store: Any) -> VectorStoreProtocol:
    """Fail fast when a provided store does not satisfy SDK retrieval contract."""
    if not isinstance(vector_store, VectorStoreProtocol):
        logger.error(
            "Vector store compatibility check failed missing similarity_search type=%s",
            type(vector_store).__name__,
        )
        raise SDKConfigurationError(
            "vector_store must implement similarity_search(query, k, filter=None)."
        )

    method = getattr(vector_store, "similarity_search", None)
    if not callable(method):
        logger.error(
            "Vector store compatibility check failed similarity_search not callable type=%s",
            type(vector_store).__name__,
        )
        raise SDKConfigurationError(
            "vector_store must implement callable similarity_search(query, k, filter=None)."
        )

    try:
        signature = inspect.signature(method)
        signature.bind_partial("contract-probe", 1, filter=None)
    except (TypeError, ValueError) as exc:
        logger.error(
            "Vector store compatibility check failed invalid similarity_search signature type=%s error=%s",
            type(vector_store).__name__,
            exc,
        )
        raise SDKConfigurationError(
            "vector_store similarity_search must accept (query, k, filter=None)."
        ) from exc

    logger.info(
        "Vector store compatibility check passed vector_store_type=%s",
        type(vector_store).__name__,
    )
    return cast(VectorStoreProtocol, vector_store)
