from schemas import SubQueryExecutionResult, SubQueryRetrievalResult

_MAX_SNIPPET_LENGTH = 220


def _trim_snippet(text: str) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= _MAX_SNIPPET_LENGTH:
        return normalized
    return f"{normalized[:_MAX_SNIPPET_LENGTH].rstrip()}..."


def _summarize_validated_result(result: SubQueryRetrievalResult) -> str:
    if result.tool == "internal":
        if not result.internal_results:
            return "No internal chunks were retained after validation."
        return " ".join(_trim_snippet(chunk.content) for chunk in result.internal_results[:2])

    if result.opened_pages:
        return " ".join(_trim_snippet(page.content) for page in result.opened_pages[:2])

    if result.web_search_results:
        return " ".join(_trim_snippet(item.snippet) for item in result.web_search_results[:2])

    return "No web pages were retained after validation."


def synthesize_answer(
    query: str,
    execution_results: list[SubQueryExecutionResult],
) -> str:
    lines = [f"Final answer for query: {query}", ""]
    for execution_result in execution_results:
        retrieval = execution_result.retrieval_result
        validation = execution_result.validation_result
        if validation.status != "validated" or not validation.sufficient:
            lines.append(
                f"- Sub-query: {retrieval.sub_query}\n"
                f"  Evidence: Insufficient validated evidence for sub-query: {retrieval.sub_query}."
            )
            continue

        lines.append(
            f"- Sub-query: {retrieval.sub_query}\n"
            f"  Evidence: {_summarize_validated_result(retrieval)}"
        )

    return "\n".join(lines).strip()
