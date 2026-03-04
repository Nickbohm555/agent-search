from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda


@dataclass
class RuntimeConfig:
    enabled: bool
    mode: str
    model: str


@dataclass
class RuntimeHandle:
    config: RuntimeConfig
    runnable: Optional[Runnable[Any, str]]
    initialized: bool
    status: str

    @property
    def enabled(self) -> bool:
        return self.config.enabled and self.initialized and self.runnable is not None

    def synthesize(self, query: str, evidence: str, fallback_output: str) -> str:
        if not self.enabled or self.runnable is None:
            return fallback_output

        try:
            text = self.runnable.invoke({"query": query, "evidence": evidence})
        except Exception:
            return fallback_output

        if isinstance(text, str) and text.strip():
            return text.strip()
        return fallback_output


def _read_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_runtime_config() -> RuntimeConfig:
    return RuntimeConfig(
        enabled=_read_bool_env("AGENT_RUNTIME_ENABLED", False),
        mode=os.getenv("AGENT_RUNTIME_MODE", "disabled").strip().lower(),
        model=os.getenv("AGENT_RUNTIME_MODEL", "gpt-4o-mini").strip(),
    )


def _build_stub_runnable() -> Runnable[Any, str]:
    def _render(inputs: dict[str, str]) -> str:
        query = inputs.get("query", "").strip()
        evidence = " ".join(inputs.get("evidence", "").split())
        if not evidence:
            evidence = "No validated evidence available."
        return (
            f"Stub runtime answer for: {query}\n"
            f"Validated evidence summary: {evidence}"
        )

    return RunnableLambda(_render)


def _build_langchain_openai_runnable(model_name: str) -> Optional[Runnable[Any, str]]:
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You synthesize concise answers from validated evidence only."),
            (
                "human",
                "User query: {query}\nValidated evidence:\n{evidence}\n"
                "Return a concise answer based only on the validated evidence.",
            ),
        ]
    )
    model = ChatOpenAI(model=model_name, temperature=0)
    return prompt | model | RunnableLambda(lambda message: str(message.content))


def initialize_runtime_handle() -> RuntimeHandle:
    config = load_runtime_config()

    if not config.enabled:
        return RuntimeHandle(
            config=config,
            runnable=None,
            initialized=False,
            status="disabled_by_config",
        )

    if config.mode == "stub":
        return RuntimeHandle(
            config=config,
            runnable=_build_stub_runnable(),
            initialized=True,
            status="enabled_stub",
        )

    if config.mode == "langchain_openai":
        try:
            runnable = _build_langchain_openai_runnable(config.model)
        except Exception:
            runnable = None

        if runnable is None:
            return RuntimeHandle(
                config=config,
                runnable=None,
                initialized=False,
                status="missing_openai_config",
            )

        return RuntimeHandle(
            config=config,
            runnable=runnable,
            initialized=True,
            status="enabled_langchain_openai",
        )

    return RuntimeHandle(
        config=config,
        runnable=None,
        initialized=False,
        status="unsupported_mode",
    )
