from typing import Literal

ToolName = Literal["internal", "web"]

_INTERNAL_CUES = (
    "internal",
    "docs",
    "documentation",
    "knowledge base",
    "kb",
    "runbook",
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
    "competitor",
    "market",
)


def _contains_any_cue(text: str, cues: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(cue in lowered for cue in cues)


def select_tool_for_sub_query(sub_query: str) -> ToolName:
    has_web_cue = _contains_any_cue(sub_query, _WEB_CUES)
    has_internal_cue = _contains_any_cue(sub_query, _INTERNAL_CUES)

    if has_web_cue and not has_internal_cue:
        return "web"
    if has_internal_cue and not has_web_cue:
        return "internal"
    if has_web_cue:
        return "web"
    return "internal"


def assign_tools_to_sub_queries(sub_queries: list[str]) -> list[tuple[str, ToolName]]:
    return [(sub_query, select_tool_for_sub_query(sub_query)) for sub_query in sub_queries]
