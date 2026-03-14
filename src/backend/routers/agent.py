import logging
import os
import json
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from agent_search.errors import SDKConfigurationError
from agent_search.public_api import advanced_rag as sdk_advanced_rag
from agent_search.public_api import cancel_run as sdk_cancel_run
from agent_search.public_api import get_run_status as sdk_get_run_status
from agent_search.public_api import resume_run as sdk_resume_run
from agent_search.public_api import run_async as sdk_run_async
from agent_search.runtime.jobs import get_agent_run_job, iter_agent_run_events, restore_agent_run_job
from db import DATABASE_URL
from db import get_db
from schemas import (
    RuntimeAgentRunAsyncCancelResponse,
    RuntimeAgentRunAsyncStartResponse,
    RuntimeAgentRunAsyncStatusResponse,
    RuntimeAgentRunRequest,
    RuntimeAgentRunResumeRequest,
    RuntimeAgentRunResponse,
)
from services.vector_store_service import get_vector_store
from utils.embeddings import get_embedding_model

router = APIRouter(prefix="/api/agents", tags=["agents"])
logger = logging.getLogger(__name__)

_VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")
_ROUTER_MODEL_NAME = os.getenv("DECOMPOSITION_ONLY_MODEL", os.getenv("RUNTIME_AGENT_MODEL", "gpt-4.1-mini")).strip() or (
    "gpt-4.1-mini"
)
_ROUTER_MODEL_TEMPERATURE = float(os.getenv("DECOMPOSITION_ONLY_TEMPERATURE", "0"))


def _build_sdk_runtime_dependencies() -> tuple[object, object]:
    vector_store = get_vector_store(
        connection=DATABASE_URL,
        collection_name=_VECTOR_COLLECTION_NAME,
        embeddings=get_embedding_model(),
    )
    model = ChatOpenAI(
        model=_ROUTER_MODEL_NAME,
        temperature=_ROUTER_MODEL_TEMPERATURE,
    )
    logger.info(
        "Agent router dependencies resolved collection_name=%s model=%s",
        _VECTOR_COLLECTION_NAME,
        _ROUTER_MODEL_NAME,
    )
    return vector_store, model


def _build_run_config(payload: RuntimeAgentRunRequest) -> dict[str, Any] | None:
    config: dict[str, Any] = {}
    if payload.custom_prompts is not None:
        config["custom_prompts"] = payload.custom_prompts.model_dump(exclude_none=True)

    if payload.runtime_config is not None:
        config["runtime_config"] = payload.runtime_config.model_dump(exclude_none=True)

    controls = payload.controls
    if controls is not None:
        if controls.rerank is not None:
            config["rerank"] = controls.rerank.model_dump(exclude_none=True)
        if controls.query_expansion is not None:
            config["query_expansion"] = controls.query_expansion.model_dump(exclude_none=True)
        if controls.hitl is not None:
            config["hitl"] = controls.hitl.model_dump(exclude_none=True)

    return config or None


def _resolve_checkpoint_db_url(payload: RuntimeAgentRunRequest) -> str | None:
    if payload.checkpoint_db_url is not None and payload.checkpoint_db_url.strip():
        return payload.checkpoint_db_url

    controls = payload.controls
    if controls is None or controls.hitl is None or not controls.hitl.enabled:
        return None

    # The app runs against the local Postgres service, so enable checkpointed HITL
    # automatically at the HTTP layer without changing the SDK contract.
    return DATABASE_URL


def _normalize_resume_payload_for_sdk(resume: object) -> object:
    if hasattr(resume, "model_dump"):
        return resume.model_dump(exclude_none=True)
    return resume


def _encode_sse_event(event: object) -> str:
    payload = json.dumps(event.model_dump(mode="json"), separators=(",", ":"))
    return f"id: {event.event_id}\nevent: {event.event_type}\ndata: {payload}\n\n"


def _restore_http_runtime_job(job_id: str, *, include_runtime_dependencies: bool = False) -> bool:
    existing_job = get_agent_run_job(job_id)
    if existing_job is not None and (
        not include_runtime_dependencies
        or (existing_job.runtime_model is not None and existing_job.runtime_vector_store is not None)
    ):
        return True
    if include_runtime_dependencies:
        vector_store, model = _build_sdk_runtime_dependencies()
        return restore_agent_run_job(job_id, model=model, vector_store=vector_store) is not None
    return restore_agent_run_job(job_id) is not None


@router.post("/run", response_model=RuntimeAgentRunResponse)
def runtime_agent_run(
    payload: RuntimeAgentRunRequest,
    db: Session = Depends(get_db),
) -> RuntimeAgentRunResponse:
    del db
    vector_store, model = _build_sdk_runtime_dependencies()
    logger.info("Agent router delegating sync run query_len=%s", len(payload.query))
    return sdk_advanced_rag(
        payload.query,
        vector_store=vector_store,
        model=model,
        config=_build_run_config(payload),
        checkpoint_db_url=_resolve_checkpoint_db_url(payload),
    )


@router.post("/run-async", response_model=RuntimeAgentRunAsyncStartResponse)
def runtime_agent_run_async(payload: RuntimeAgentRunRequest) -> RuntimeAgentRunAsyncStartResponse:
    vector_store, model = _build_sdk_runtime_dependencies()
    logger.info("Agent router delegating async run query_len=%s", len(payload.query))
    return sdk_run_async(
        payload.query,
        vector_store=vector_store,
        model=model,
        config=_build_run_config(payload),
        checkpoint_db_url=_resolve_checkpoint_db_url(payload),
    )


@router.get("/run-status/{job_id}", response_model=RuntimeAgentRunAsyncStatusResponse)
def runtime_agent_run_status(job_id: str) -> RuntimeAgentRunAsyncStatusResponse:
    logger.info("Agent router delegating async status job_id=%s", job_id)
    _restore_http_runtime_job(job_id)
    try:
        return sdk_get_run_status(job_id)
    except SDKConfigurationError:
        raise HTTPException(status_code=404, detail="Job not found.")


@router.get("/run-events/{job_id}")
def runtime_agent_run_events(
    job_id: str,
    after_event_id: str | None = None,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    effective_after_event_id = last_event_id or after_event_id
    logger.info(
        "Agent router streaming lifecycle events job_id=%s last_event_id=%s after_event_id=%s",
        job_id,
        last_event_id,
        after_event_id,
    )
    if not _restore_http_runtime_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")

    def event_stream():
        for event in iter_agent_run_events(job_id, after_event_id=effective_after_event_id):
            yield _encode_sse_event(event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/run-cancel/{job_id}", response_model=RuntimeAgentRunAsyncCancelResponse)
def runtime_agent_run_cancel(job_id: str) -> RuntimeAgentRunAsyncCancelResponse:
    logger.info("Agent router delegating async cancel job_id=%s", job_id)
    try:
        return sdk_cancel_run(job_id)
    except SDKConfigurationError:
        raise HTTPException(status_code=404, detail="Job not found or already finished.")


@router.post("/run-resume/{job_id}", response_model=RuntimeAgentRunAsyncStatusResponse)
def runtime_agent_run_resume(job_id: str, payload: RuntimeAgentRunResumeRequest) -> RuntimeAgentRunAsyncStatusResponse:
    logger.info("Agent router delegating async resume job_id=%s", job_id)
    _restore_http_runtime_job(job_id, include_runtime_dependencies=True)
    try:
        return sdk_resume_run(job_id, resume=_normalize_resume_payload_for_sdk(payload.resume))
    except SDKConfigurationError as exc:
        detail = str(exc)
        if detail == "Job not found.":
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=409, detail=detail)
