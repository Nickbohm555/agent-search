from __future__ import annotations

import logging
import os
from typing import Any

from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from agents import create_coordinator_agent
from db import DATABASE_URL
from schemas import RuntimeAgentRunRequest, RuntimeAgentRunResponse
from services.vector_store_service import get_vector_store
from utils.agent_callbacks import AgentLoggingCallbackHandler, log_agent_messages_summary
from utils.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

_VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")
_RUNTIME_AGENT_MODEL = os.getenv("RUNTIME_AGENT_MODEL", "gpt-4.1-mini")


_QUERY_LOG_MAX = 200


def _truncate_query(q: str) -> str:
    return q[: _QUERY_LOG_MAX] + "..." if len(q) > _QUERY_LOG_MAX else q


def _extract_last_message_content(result: Any) -> str:
    messages = result.get("messages") if isinstance(result, dict) else None
    if not isinstance(messages, list) or not messages:
        raise ValueError("Agent invoke result missing non-empty messages list.")

    last_message = messages[-1]
    content = getattr(last_message, "content", None)
    if isinstance(content, str):
        return content
    if content is None:
        raise ValueError("Agent invoke result last message content is empty.")
    return str(content)


def run_runtime_agent(payload: RuntimeAgentRunRequest, db: Session) -> RuntimeAgentRunResponse:
    """Run the coordinator runtime agent for a user query."""
    logger.info(
        "Runtime agent run start query=%s query_length=%s",
        _truncate_query(payload.query),
        len(payload.query),
    )
    vector_store = get_vector_store(
        connection=DATABASE_URL,
        collection_name=_VECTOR_COLLECTION_NAME,
        embeddings=get_embedding_model(),
    )
    agent = create_coordinator_agent(
        vector_store=vector_store,
        model=_RUNTIME_AGENT_MODEL,
    )
    callbacks = [AgentLoggingCallbackHandler()]
    config = {"callbacks": callbacks}
    result = agent.invoke(
        {"messages": [HumanMessage(content=payload.query)]},
        config=config,
    )
    messages = result.get("messages") if isinstance(result, dict) else []
    if isinstance(messages, list) and messages:
        logger.info("Agent run finished; logging tool calls and tool results from %s messages", len(messages))
        log_agent_messages_summary(messages)
    output = _extract_last_message_content(result)
    logger.info(
        "Runtime agent run complete output_length=%s output_preview=%s",
        len(output),
        output[:200] + "..." if len(output) > 200 else output,
    )
    return RuntimeAgentRunResponse(output=output)
