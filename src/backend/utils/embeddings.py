import hashlib
import math
import re

EMBEDDING_DIM = 16


_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_PATTERN.finditer(text)]


def chunk_text(text: str, chunk_size: int = 60, overlap: int = 10) -> list[str]:
    """Create deterministic word chunks suitable for retrieval.

    The defaults keep chunks readable for tests and local demo usage.
    """
    words = text.split()
    if not words:
        return []

    step = max(chunk_size - overlap, 1)
    chunks: list[str] = []
    for start in range(0, len(words), step):
        window = words[start : start + chunk_size]
        if not window:
            continue
        chunks.append(" ".join(window).strip())
        if start + chunk_size >= len(words):
            break
    return chunks


def embed_text(text: str, dimensions: int = EMBEDDING_DIM) -> list[float]:
    """Generate a deterministic local embedding for scaffold-only retrieval.

    This avoids external network/model dependencies while still enabling
    similarity-based retrieval in tests and local development.
    """
    vector = [0.0] * dimensions
    tokens = _tokenize(text)
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        magnitude = 1.0 + (digest[5] / 255.0)
        vector[bucket] += sign * magnitude

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Embedding dimensions must match")
    return sum(a * b for a, b in zip(left, right))
