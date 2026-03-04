from fastapi import APIRouter

from schemas import RuntimeAgentInfo, RuntimeAgentRunRequest, RuntimeAgentRunResponse
from services.agent_service import get_runtime_agent_info, run_runtime_agent

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/runtime", response_model=RuntimeAgentInfo)
def runtime_agent_info() -> RuntimeAgentInfo:
    return get_runtime_agent_info()


@router.post("/run", response_model=RuntimeAgentRunResponse)
def runtime_agent_run(payload: RuntimeAgentRunRequest) -> RuntimeAgentRunResponse:
    return run_runtime_agent(payload)
