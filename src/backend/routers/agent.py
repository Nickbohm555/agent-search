import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from agent_search.errors import SDKConfigurationError
from agent_search.public_api import advanced_rag as sdk_advanced_rag
from agent_search.public_api import cancel_run as sdk_cancel_run
from agent_search.public_api import get_run_status as sdk_get_run_status
from agent_search.public_api import run_async as sdk_run_async
from db import DATABASE_URL
from db import get_db
from schemas import (
    RuntimeAgentRunAsyncCancelResponse,
    RuntimeAgentRunAsyncStartResponse,
    RuntimeAgentRunAsyncStatusResponse,
    RuntimeAgentRunRequest,
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


def _build_thread_config(thread_id: str | None) -> dict[str, str] | None:
    if thread_id is None:
        return None
    return {"thread_id": thread_id}


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
        config=_build_thread_config(payload.thread_id),
    )


@router.post("/run-async", response_model=RuntimeAgentRunAsyncStartResponse)
def runtime_agent_run_async(payload: RuntimeAgentRunRequest) -> RuntimeAgentRunAsyncStartResponse:
    vector_store, model = _build_sdk_runtime_dependencies()
    logger.info("Agent router delegating async run query_len=%s", len(payload.query))
    return sdk_run_async(
        payload.query,
        vector_store=vector_store,
        model=model,
        config=_build_thread_config(payload.thread_id),
    )


@router.get("/run-status/{job_id}", response_model=RuntimeAgentRunAsyncStatusResponse)
def runtime_agent_run_status(job_id: str) -> RuntimeAgentRunAsyncStatusResponse:
    logger.info("Agent router delegating async status job_id=%s", job_id)
    try:
        return sdk_get_run_status(job_id)
    except SDKConfigurationError:
        raise HTTPException(status_code=404, detail="Job not found.")


@router.post("/run-cancel/{job_id}", response_model=RuntimeAgentRunAsyncCancelResponse)
def runtime_agent_run_cancel(job_id: str) -> RuntimeAgentRunAsyncCancelResponse:
    logger.info("Agent router delegating async cancel job_id=%s", job_id)
    try:
        return sdk_cancel_run(job_id)
    except SDKConfigurationError:
        raise HTTPException(status_code=404, detail="Job not found or already finished.")
