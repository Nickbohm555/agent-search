import asyncio
from threading import Thread

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from db import get_db
from schemas import (
    RuntimeAgentInfo,
    RuntimeAgentRunRequest,
    RuntimeAgentRunResponse,
    RuntimeAgentStreamEvent,
)
from services.agent_service import (
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
    event_queue: asyncio.Queue[RuntimeAgentStreamEvent | None] = asyncio.Queue()
    event_loop = asyncio.get_running_loop()
    sequence = 1

    def enqueue_stream_event(event_name: str, data: dict) -> None:
        nonlocal sequence
        stream_event = RuntimeAgentStreamEvent(
            sequence=sequence,
            event=event_name,
            data=data,
        )
        sequence += 1
        event_loop.call_soon_threadsafe(event_queue.put_nowait, stream_event)

    def run_agent_in_background() -> None:
        try:
            response = run_runtime_agent(
                payload,
                db=db,
                tracing_handle=request.app.state.langfuse,
                runtime_handle=request.app.state.runtime_model,
                stream_event_callback=enqueue_stream_event,
            )
            enqueue_stream_event(
                "completed",
                {
                    "agent_name": response.agent_name,
                    "output": response.output,
                    "graph_state": response.graph_state.model_dump()
                    if response.graph_state is not None
                    else None,
                },
            )
        except Exception as exc:  # pragma: no cover - defensive fallback path
            enqueue_stream_event(
                "error",
                {
                    "message": f"Run failed: {exc}",
                },
            )
        finally:
            event_loop.call_soon_threadsafe(event_queue.put_nowait, None)

    Thread(target=run_agent_in_background, daemon=True).start()

    async def event_generator():
        while True:
            stream_event = await event_queue.get()
            if stream_event is None:
                break
            if await request.is_disconnected():
                break
            yield (
                f"event: {stream_event.event}\n"
                f"data: {stream_event.model_dump_json()}\n\n"
            )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
