from sqlalchemy.orm import Session

from schemas import (
    InternalDataRetrieveRequest,
    SubQueryRetrievalResult,
    SubQueryValidationAttempt,
    SubQueryValidationResult,
)
from services.internal_data_service import retrieve_internal_data
from services.web_service import run_web_search_then_open

_MIN_WEB_CONTENT_CHARS = 80
_MAX_VALIDATION_ATTEMPTS = 2


def _is_result_sufficient(result: SubQueryRetrievalResult) -> bool:
    if result.tool == "internal":
        return len(result.internal_results) > 0

    return any(len(page.content.strip()) >= _MIN_WEB_CONTENT_CHARS for page in result.opened_pages)


def _build_attempt_snapshot(
    attempt: int,
    sufficient: bool,
    result: SubQueryRetrievalResult,
    follow_up_action: str | None = None,
) -> SubQueryValidationAttempt:
    return SubQueryValidationAttempt(
        attempt=attempt,
        sufficient=sufficient,
        internal_result_count=len(result.internal_results),
        opened_page_count=len(result.opened_pages),
        follow_up_action=follow_up_action,
    )


def _run_follow_up_retrieval(
    result: SubQueryRetrievalResult,
    db: Session,
    attempt: int,
) -> tuple[SubQueryRetrievalResult, str]:
    if result.tool == "internal":
        expanded_limit = min(5 + attempt * 3, 20)
        response = retrieve_internal_data(
            InternalDataRetrieveRequest(query=result.sub_query, limit=expanded_limit),
            db,
        )
        return (
            result.model_copy(
                update={
                    "internal_results": response.results,
                    "web_search_results": [],
                    "opened_urls": [],
                    "opened_pages": [],
                }
            ),
            "search_more_internal",
        )

    web_run = run_web_search_then_open(
        result.sub_query,
        search_limit=min(5 + attempt, 10),
        open_limit=min(1 + attempt, 3),
    )
    return (
        result.model_copy(
            update={
                "internal_results": [],
                "web_search_results": web_run.search_results,
                "opened_urls": web_run.opened_urls,
                "opened_pages": web_run.opened_pages,
            }
        ),
        "open_more_web_pages",
    )


def validate_retrieval_result(
    retrieval_result: SubQueryRetrievalResult,
    db: Session,
    max_attempts: int = _MAX_VALIDATION_ATTEMPTS,
) -> tuple[SubQueryRetrievalResult, SubQueryValidationResult]:
    current_result = retrieval_result
    follow_up_actions: list[str] = []
    attempt_trace: list[SubQueryValidationAttempt] = []

    for attempt in range(1, max_attempts + 1):
        sufficient = _is_result_sufficient(current_result)
        if sufficient:
            attempt_trace.append(_build_attempt_snapshot(attempt, sufficient, current_result))
            return current_result, SubQueryValidationResult(
                sub_query=current_result.sub_query,
                tool=current_result.tool,
                sufficient=True,
                status="validated",
                attempts=attempt,
                follow_up_actions=follow_up_actions,
                attempt_trace=attempt_trace,
                stop_reason="sufficient_evidence",
            )

        if attempt == max_attempts:
            attempt_trace.append(_build_attempt_snapshot(attempt, sufficient, current_result))
            return current_result, SubQueryValidationResult(
                sub_query=current_result.sub_query,
                tool=current_result.tool,
                sufficient=False,
                status="stopped_insufficient",
                attempts=attempt,
                follow_up_actions=follow_up_actions,
                attempt_trace=attempt_trace,
                stop_reason="max_attempts_reached",
            )

        current_result, action = _run_follow_up_retrieval(current_result, db, attempt)
        follow_up_actions.append(action)
        attempt_trace.append(
            _build_attempt_snapshot(attempt, sufficient, current_result, follow_up_action=action)
        )

    return current_result, SubQueryValidationResult(
        sub_query=current_result.sub_query,
        tool=current_result.tool,
        sufficient=False,
        status="stopped_insufficient",
        attempts=max_attempts,
        follow_up_actions=follow_up_actions,
        attempt_trace=attempt_trace,
        stop_reason="max_attempts_reached",
    )


def validate_retrieval_results(
    retrieval_results: list[SubQueryRetrievalResult],
    db: Session,
) -> tuple[list[SubQueryRetrievalResult], list[SubQueryValidationResult]]:
    validated_results: list[SubQueryRetrievalResult] = []
    validation_results: list[SubQueryValidationResult] = []

    for retrieval_result in retrieval_results:
        validated_retrieval, validation_result = validate_retrieval_result(retrieval_result, db)
        validated_results.append(validated_retrieval)
        validation_results.append(validation_result)

    return validated_results, validation_results
