from sqlalchemy.orm import Session

from schemas import (
    InternalDataRetrieveRequest,
    SubQueryRetrievalResult,
    SubQueryToolAssignment,
)
from services.internal_data_service import retrieve_internal_data
from services.web_service import run_web_search_then_open


def execute_subquery_retrieval(
    assignment: SubQueryToolAssignment,
    db: Session,
    internal_limit: int = 5,
    web_search_limit: int = 5,
    web_open_limit: int = 1,
) -> SubQueryRetrievalResult:
    if assignment.tool == "internal":
        internal_response = retrieve_internal_data(
            InternalDataRetrieveRequest(query=assignment.sub_query, limit=internal_limit),
            db,
        )
        return SubQueryRetrievalResult(
            sub_query=assignment.sub_query,
            tool="internal",
            internal_results=internal_response.results,
        )

    web_run = run_web_search_then_open(
        assignment.sub_query,
        search_limit=web_search_limit,
        open_limit=web_open_limit,
    )
    return SubQueryRetrievalResult(
        sub_query=assignment.sub_query,
        tool="web",
        web_search_results=web_run.search_results,
        opened_urls=web_run.opened_urls,
        opened_pages=web_run.opened_pages,
    )


def execute_subquery_retrievals(
    assignments: list[SubQueryToolAssignment],
    db: Session,
) -> list[SubQueryRetrievalResult]:
    return [execute_subquery_retrieval(assignment, db) for assignment in assignments]
