from __future__ import annotations

import hashlib
from functools import lru_cache

from langchain_core.embeddings import Embeddings

# Keep in sync with vector column size in models.py / pgvector storage.
EMBEDDING_DIM = 1536


class DeterministicHashEmbeddings(Embeddings):
    """Local deterministic embeddings for scaffold/dev usage."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_text(text)

    def _embed_text(self, text: str) -> list[float]:
        seed = text.encode("utf-8")
        values: list[float] = []
        counter = 0

        # Expand SHA-256 output into a stable EMBEDDING_DIM-length vector.
        while len(values) < EMBEDDING_DIM:
            digest = hashlib.sha256(seed + counter.to_bytes(4, byteorder="big")).digest()
            for i in range(0, len(digest), 4):
                chunk = digest[i : i + 4]
                integer = int.from_bytes(chunk, byteorder="big", signed=False)
                values.append((integer / 0xFFFFFFFF) * 2.0 - 1.0)
                if len(values) == EMBEDDING_DIM:
                    break
            counter += 1
        return values


@lru_cache(maxsize=1)
def get_embedding_model() -> Embeddings:
    return DeterministicHashEmbeddings()
