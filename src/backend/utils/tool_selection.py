import re
from typing import Literal

ToolName = Literal["internal_rag", "web_search"]

_INTERNAL_HINTS = [
    "internal",
    "our",
    "company",
    "team",
    "policy",
    "wiki",
    "playbook",
    "roadmap",
    "document",
    "docs",
    "notion",
    "google doc",
]

_WEB_HINTS = [
    "latest",
    "current",
    "today",
    "news",
    "public",
    "release",
    "price",
    "weather",
    "stock",
    "world",
    "wikipedia",
    "official",
]


def _count_matches(text: str, hints: list[str]) -> int:
    return sum(1 for hint in hints if re.search(rf"\b{re.escape(hint)}\b", text, re.IGNORECASE))


def select_tool_for_subquery(subquery: str) -> ToolName:
    """Assign exactly one retrieval tool per sub-query."""
    internal_score = _count_matches(subquery, _INTERNAL_HINTS)
    web_score = _count_matches(subquery, _WEB_HINTS)

    if internal_score > web_score:
        return "internal_rag"
    return "web_search"
