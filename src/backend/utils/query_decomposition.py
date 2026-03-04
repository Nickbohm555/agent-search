import re

_SPLIT_PATTERN = re.compile(r"\s+(?:and|then|also)\s+|[;\n]+", re.IGNORECASE)


def decompose_query(query: str) -> list[str]:
    """Break a user query into focused sub-queries for retrieval."""
    normalized = " ".join(query.strip().split())
    if not normalized:
        return []

    candidates = _SPLIT_PATTERN.split(normalized)
    subqueries: list[str] = []
    for candidate in candidates:
        cleaned = candidate.strip(" ,.?!")
        if not cleaned:
            continue
        # Avoid very broad comma-heavy clauses by splitting once more.
        if "," in cleaned and len(cleaned) > 120:
            comma_parts = [part.strip(" ,.?!") for part in cleaned.split(",") if part.strip(" ,.?!")]
            subqueries.extend(comma_parts)
            continue
        subqueries.append(cleaned)

    if not subqueries:
        return [normalized.strip(" ,.?!")]

    # Keep order while removing duplicates.
    deduped: list[str] = []
    seen: set[str] = set()
    for subquery in subqueries:
        lowered = subquery.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(subquery)
    return deduped
