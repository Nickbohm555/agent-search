from typing import Iterable


def validate_embedding_length(values: Iterable[float], expected: int = 1536) -> list[float]:
    vector = list(values)
    if len(vector) != expected:
        raise ValueError(f"Embedding must have {expected} dimensions")
    return vector
