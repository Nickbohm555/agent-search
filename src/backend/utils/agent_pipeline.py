from schemas import AgentPlanResponse, AgentProgressEvent, AgentSubquery
from utils.query_decomposition import decompose_query
from utils.tool_selection import select_tool_for_subquery


def build_agent_plan(query: str) -> AgentPlanResponse:
    subquery_texts = decompose_query(query)
    subqueries = [
        AgentSubquery(id=index + 1, text=text, tool=select_tool_for_subquery(text))
        for index, text in enumerate(subquery_texts)
    ]
    events = [
        AgentProgressEvent(step="decomposition", status="completed", detail=f"generated_{len(subqueries)}_subqueries"),
        AgentProgressEvent(step="tool_selection", status="completed", detail="assigned_one_tool_per_subquery"),
    ]
    return AgentPlanResponse(
        query=query,
        trajectory=["decomposition", "tool_selection"],
        subqueries=subqueries,
        events=events,
    )
