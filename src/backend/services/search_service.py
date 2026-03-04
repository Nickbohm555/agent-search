from schemas import SearchSkeletonResponse


def get_search_scaffold() -> SearchSkeletonResponse:
    return SearchSkeletonResponse(
        status="scaffold",
        message="search pipeline not implemented yet",
    )
