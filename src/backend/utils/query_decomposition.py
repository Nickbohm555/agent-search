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

_COARSE_SPLIT_PATTERN = re.compile(r"[?;]+")
_CONNECTOR_SPLIT_PATTERN = re.compile(
    r"\b(?:and|then|also|plus|with|vs\.?|versus|against|while)\b",
    flags=re.IGNORECASE,
)
_POLITE_PREFIX_PATTERN = re.compile(
    r"^(?:please|kindly|can you|could you|would you|help me)\s+",
    flags=re.IGNORECASE,
)


def _normalize_query(query: str) -> str:
    return re.sub(r"\s+", " ", query).strip()


def _contains_cue(text: str, cues: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(cue in lowered for cue in cues)


def _strip_connectors(segment: str) -> str:
    return re.sub(r"^(and|then|also|plus)\s+", "", segment.strip(), flags=re.IGNORECASE)


def _sanitize_segment(segment: str) -> str:
    return _strip_connectors(segment).strip(" .,;:!?")


def _dedupe_key(segment: str) -> str:
    lowered = _POLITE_PREFIX_PATTERN.sub("", segment.strip().lower())
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip(" .,;:!?")


def _split_mixed_domain_segment(segment: str) -> list[str]:
    if not (_contains_cue(segment, _INTERNAL_CUES) and _contains_cue(segment, _WEB_CUES)):
        return [segment]

    split_parts = _CONNECTOR_SPLIT_PATTERN.split(segment)
    cleaned = [_sanitize_segment(part) for part in split_parts]
    return [part for part in cleaned if part]


def decompose_query(query: str) -> list[str]:
    normalized_query = _normalize_query(query)
    if not normalized_query:
        return []

    coarse_segments = _COARSE_SPLIT_PATTERN.split(normalized_query)
    ordered_subqueries: list[str] = []
    seen: set[str] = set()

    for segment in coarse_segments:
        cleaned_segment = _sanitize_segment(segment)
        if not cleaned_segment:
            continue

        for candidate in _split_mixed_domain_segment(cleaned_segment):
            dedupe_key = _dedupe_key(candidate)
            if not dedupe_key or dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            ordered_subqueries.append(candidate)

    if ordered_subqueries:
        return ordered_subqueries

    return [normalized_query]
