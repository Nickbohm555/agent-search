from fastapi import APIRouter

from schemas import AgentPlanRequest, AgentPlanResponse
from utils.agent_pipeline import build_agent_plan

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/plan", response_model=AgentPlanResponse)
def plan_agent_run(payload: AgentPlanRequest) -> AgentPlanResponse:
    return build_agent_plan(payload.query)
