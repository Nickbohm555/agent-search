from __future__ import annotations

import json
import logging
import os
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from sqlalchemy.orm import Session

from agents import create_coordinator_agent
from db import DATABASE_URL
from schemas import RuntimeAgentRunRequest, RuntimeAgentRunResponse, SubQuestionAnswer
from services.vector_store_service import get_vector_store
from utils.agent_callbacks import AgentLoggingCallbackHandler, log_agent_messages_summary
from utils.embeddings import get_embedding_model

logger = logging.getLogger(__name__)

_VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "agent_search_internal_data")
_RUNTIME_AGENT_MODEL = os.getenv("RUNTIME_AGENT_MODEL", "gpt-4.1-mini")
_MAIN_AGENT_TASK_TOOL_NAME = "task"


_QUERY_LOG_MAX = 200


def _truncate_query(q: str) -> str:
    return q[: _QUERY_LOG_MAX] + "..." if len(q) > _QUERY_LOG_MAX else q


def _stringify_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return str(content)


def _is_main_agent_turn(msg: AIMessage) -> bool:
    tool_calls = getattr(msg, "tool_calls", None)
    if not isinstance(tool_calls, list):
        return False
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        if tool_call.get("name") == _MAIN_AGENT_TASK_TOOL_NAME:
            return True
    return False


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


def _extract_sub_qa(messages: list[BaseMessage]) -> list[SubQuestionAnswer]:
    tool_results_by_call_id: dict[str, str] = {}
    tool_message_indices_by_call_id: dict[str, int] = {}
    for i, msg in enumerate(messages):
        if not isinstance(msg, ToolMessage):
            continue
        tool_call_id = getattr(msg, "tool_call_id", None)
        if not isinstance(tool_call_id, str) or not tool_call_id:
            continue
        content = getattr(msg, "content", "")
        content_str = _stringify_message_content(content)
        tool_results_by_call_id[tool_call_id] = content_str
        tool_message_indices_by_call_id[tool_call_id] = i

    sub_qa: list[SubQuestionAnswer] = []
    sub_qa_index_by_call_id: dict[str, int] = {}
    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        tool_calls = getattr(msg, "tool_calls", None)
        if not isinstance(tool_calls, list):
            continue
        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            tool_call_id = tool_call.get("id")
            if not isinstance(tool_call_id, str) or not tool_call_id:
                continue
            args = tool_call.get("args")
            sub_question = ""
            tool_call_input = ""
            if isinstance(args, dict):
                tool_call_input = json.dumps(args)
                for key in ("sub_question", "question", "query", "input"):
                    value = args.get(key)
                    if isinstance(value, str) and value.strip():
                        sub_question = value
                        break
                if not sub_question:
                    sub_question = str(args)
            elif isinstance(args, str):
                sub_question = args
                tool_call_input = args
            elif args is not None:
                sub_question = str(args)
                tool_call_input = str(args)

            if not sub_question:
                continue
            sub_answer = tool_results_by_call_id.get(tool_call_id)
            if sub_answer is None:
                continue
            sub_qa.append(
                SubQuestionAnswer(
                    sub_question=sub_question,
                    sub_answer=sub_answer,
                    tool_call_input=tool_call_input,
                )
            )
            sub_qa_index_by_call_id[tool_call_id] = len(sub_qa) - 1
            logger.info(
                "Extracted sub_qa item tool_call_id=%s sub_question=%s tool_call_input=%s",
                tool_call_id,
                _truncate_query(sub_question),
                _truncate_query(tool_call_input),
            )

    for tool_call_id, sub_qa_index in sub_qa_index_by_call_id.items():
        tool_message_index = tool_message_indices_by_call_id.get(tool_call_id)
        if tool_message_index is None:
            continue
        last_sub_agent_response = ""
        for later_msg in messages[tool_message_index + 1 :]:
            if not isinstance(later_msg, AIMessage):
                continue
            if _is_main_agent_turn(later_msg):
                break
            content_str = _stringify_message_content(getattr(later_msg, "content", ""))
            if content_str.strip():
                last_sub_agent_response = content_str
        sub_qa[sub_qa_index].sub_agent_response = last_sub_agent_response
        logger.info(
            "Extracted sub_agent_response tool_call_id=%s response_preview=%s",
            tool_call_id,
            _truncate_query(last_sub_agent_response),
        )

    logger.info("Extracted sub_qa pairs count=%s", len(sub_qa))
    return sub_qa


def _log_sub_qa_run_end_summary(sub_qa: list[SubQuestionAnswer]) -> None:
    logger.info("SubQuestionAnswer summary count=%s", len(sub_qa))
    for index, item in enumerate(sub_qa, start=1):
        logger.info(
            "SubQuestionAnswer[%s] sub_question=%s tool_call_input=%s sub_answer=%s sub_agent_response=%s",
            index,
            _truncate_query(item.sub_question),
            _truncate_query(item.tool_call_input),
            _truncate_query(item.sub_answer),
            _truncate_query(item.sub_agent_response),
        )


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
    sub_qa = _extract_sub_qa(messages) if isinstance(messages, list) else []
    _log_sub_qa_run_end_summary(sub_qa)
    output = _extract_last_message_content(result)
    logger.info(
        "Runtime agent run complete output_length=%s output_preview=%s",
        len(output),
        output[:200] + "..." if len(output) > 200 else output,
    )
    return RuntimeAgentRunResponse(output=output)
