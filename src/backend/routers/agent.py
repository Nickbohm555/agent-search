from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from db import get_db
from schemas import RuntimeAgentInfo, RuntimeAgentRunRequest, RuntimeAgentRunResponse
from services.agent_service import (
    build_runtime_agent_stream_events,
    get_runtime_agent_info,
    run_runtime_agent,
)

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/runtime", response_model=RuntimeAgentInfo)
def runtime_agent_info() -> RuntimeAgentInfo:
    return get_runtime_agent_info()


@router.post("/run", response_model=RuntimeAgentRunResponse)
def runtime_agent_run(
    payload: RuntimeAgentRunRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> RuntimeAgentRunResponse:
    return run_runtime_agent(
        payload,
        db=db,
        tracing_handle=request.app.state.langfuse,
        runtime_handle=request.app.state.runtime_model,
    )


@router.post("/run/stream")
async def runtime_agent_run_stream(
    payload: RuntimeAgentRunRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    response = run_runtime_agent(
        payload,
        db=db,
        tracing_handle=request.app.state.langfuse,
        runtime_handle=request.app.state.runtime_model,
    )
    stream_events = build_runtime_agent_stream_events(response)

    async def event_generator():
        for stream_event in stream_events:
            if await request.is_disconnected():
                break
            yield (
                f"event: {stream_event.event}\n"
                f"data: {stream_event.model_dump_json()}\n\n"
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
