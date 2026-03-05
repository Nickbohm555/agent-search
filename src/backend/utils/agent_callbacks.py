"""Callback handler for agent invoke logging: tools, chains, and message summary."""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import LLMResult
from langchain_core.agents import AgentAction, AgentFinish

logger = logging.getLogger(__name__)

_MAX_LOG_INPUT = 500
_MAX_LOG_OUTPUT = 300


def _truncate(s: str, max_len: int) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


class AgentLoggingCallbackHandler(BaseCallbackHandler):
    """Logs tool calls, chain steps, and LLM usage during agent invoke."""

    @property
    def ignore_agent(self) -> bool:
        return False

    def on_chain_start(
        self,
        serialized: dict[str, Any] | None,
        inputs: dict[str, Any] | None,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        serialized = serialized if isinstance(serialized, dict) else {}
        name = serialized.get("name") or serialized.get("id")
        if isinstance(name, list):
            name = name[-1] if name else "unknown"
        else:
            name = name if name else "unknown"
        logger.info(
            "Agent chain start chain=%s run_id=%s",
            name,
            run_id,
        )

    def on_chain_end(
        self,
        outputs: dict[str, Any] | None,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        if isinstance(outputs, dict):
            out_repr = list(outputs.keys())
        elif outputs is not None:
            out_repr = type(outputs).__name__
        else:
            out_repr = "None"
        logger.info("Agent chain end run_id=%s output_keys=%s", run_id, out_repr)

    def on_tool_start(
        self,
        serialized: dict[str, Any] | None,
        input_str: str,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        serialized = serialized if isinstance(serialized, dict) else {}
        name = serialized.get("name", "unknown")
        input_s = input_str if isinstance(input_str, str) else str(input_str)
        logger.info(
            "Tool called: name=%s input=%s run_id=%s",
            name,
            _truncate(input_s, _MAX_LOG_INPUT),
            run_id,
        )

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        # Output may be ToolMessage, Command, str, or other; always get a string for len/truncate
        if output is None:
            output_str = ""
        elif hasattr(output, "content"):
            raw = getattr(output, "content", output)
            output_str = raw if isinstance(raw, str) else str(raw)
        else:
            output_str = str(output)
        logger.info(
            "Tool response: run_id=%s length=%s preview=%s",
            run_id,
            len(output_str),
            _truncate(output_str, _MAX_LOG_OUTPUT),
        )

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        logger.warning("Agent tool error run_id=%s error=%s", run_id, error)

    def on_llm_start(
        self,
        serialized: dict[str, Any] | None,
        prompts: list[str],
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        prompt_len = len(prompts[0]) if prompts and isinstance(prompts[0], str) else 0
        logger.info(
            "Agent LLM start run_id=%s prompt_len=%s",
            run_id,
            prompt_len,
        )

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        gen = response.generations
        if gen and gen[0]:
            g = gen[0][0]
            logger.info(
                "Agent LLM end run_id=%s output_len=%s",
                run_id,
                len(g.text) if getattr(g, "text", None) else 0,
            )

    def on_agent_action(
        self,
        action: AgentAction,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        logger.info(
            "Agent action tool=%s input=%s run_id=%s",
            action.tool,
            _truncate(str(action.tool_input), _MAX_LOG_INPUT),
            run_id,
        )

    def on_agent_finish(
        self,
        finish: AgentFinish,
        *,
        run_id: Any = None,
        parent_run_id: Any = None,
        **kwargs: Any,
    ) -> None:
        logger.info("Agent finish run_id=%s return_values_keys=%s", run_id, list(finish.return_values.keys()) if finish.return_values else [])


def log_agent_messages_summary(messages: list[BaseMessage]) -> None:
    """Log a summary of tool calls and tool results from the message list."""
    for i, msg in enumerate(messages):
        if isinstance(msg, AIMessage):
            if getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    name = tc.get("name", "?")
                    args = tc.get("args", {})
                    logger.info(
                        "Agent message[%s] AI tool_call tool=%s args=%s",
                        i,
                        name,
                        _truncate(str(args), _MAX_LOG_INPUT),
                    )
        elif isinstance(msg, ToolMessage):
            content = msg.content
            content_str = content if isinstance(content, str) else str(content) if content is not None else ""
            logger.info(
                "Agent message[%s] tool_result tool=%s content_len=%s content_preview=%s",
                i,
                getattr(msg, "name", "?"),
                len(content_str),
                _truncate(content_str, _MAX_LOG_OUTPUT),
            )
