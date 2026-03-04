import re

_INTERNAL_CUES = (
    "internal",
    "docs",
    "documentation",
    "knowledge base",
    "kb",
    "playbook",
    "handbook",
    "repository",
    "repo",
    "our",
    "company",
)

_WEB_CUES = (
    "web",
    "internet",
    "online",
    "latest",
    "news",
    "today",
    "current",
    "public",
    "external",
    "website",
    "site",
    "competitor",
    "market",
)


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query).strip()


def _contains_cue(text: str, cues: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(cue in lowered for cue in cues)


def _strip_connectors(segment: str) -> str:
    return re.sub(r"^(and|then|also|plus)\s+", "", segment.strip(), flags=re.IGNORECASE)


def _split_mixed_domain_segment(segment: str) -> list[str]:
    if not (_contains_cue(segment, _INTERNAL_CUES) and _contains_cue(segment, _WEB_CUES)):
        return [segment]

    split_parts = re.split(r"\b(?:and|then|also|plus)\b", segment, flags=re.IGNORECASE)
    cleaned = [_strip_connectors(part).strip(" .?!") for part in split_parts]
    return [part for part in cleaned if part]


def decompose_query(query: str) -> list[str]:
    normalized_query = _normalize_query(query)
    if not normalized_query:
        return []

    coarse_segments = re.split(r"[?;]+", normalized_query)
    ordered_subqueries: list[str] = []
    seen: set[str] = set()

    for segment in coarse_segments:
        cleaned_segment = _strip_connectors(segment).strip(" .?!")
        if not cleaned_segment:
            continue

        for candidate in _split_mixed_domain_segment(cleaned_segment):
            lowered_candidate = candidate.lower()
            if lowered_candidate in seen:
                continue
            seen.add(lowered_candidate)
            ordered_subqueries.append(candidate)

    if ordered_subqueries:
        return ordered_subqueries

    return [normalized_query]
