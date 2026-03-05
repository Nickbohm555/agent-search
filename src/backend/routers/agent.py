from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from schemas import RuntimeAgentRunRequest, RuntimeAgentRunResponse
from services.agent_service import run_runtime_agent

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.post("/run", response_model=RuntimeAgentRunResponse)
def runtime_agent_run(
    payload: RuntimeAgentRunRequest,
    db: Session = Depends(get_db),
) -> RuntimeAgentRunResponse:
    return run_runtime_agent(payload, db=db)
