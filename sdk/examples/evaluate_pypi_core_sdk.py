from __future__ import annotations

import importlib.metadata
import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Callable

from agent_search import advanced_rag
from agent_search.errors import SDKConfigurationError
from agent_search.vectorstore.langchain_adapter import LangChainVectorStoreAdapter
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.checkpoint.postgres import PostgresSaver


DEFAULT_CHECKPOINT_DB_URL = "postgresql+psycopg://agent_user:agent_pass@localhost:5432/agent_search"


@dataclass
class CaseResult:
    name: str
    passed: bool
    details: dict[str, Any]


class ProbeCallbackHandler(BaseCallbackHandler):
    def __init__(self) -> None:
        self.events: list[str] = []

    def on_chain_start(self, serialized: dict[str, Any] | None, inputs: dict[str, Any] | None, **kwargs: Any) -> None:
        _ = serialized, inputs, kwargs
        self.events.append("chain_start")

    def on_chain_end(self, outputs: dict[str, Any] | None, **kwargs: Any) -> None:
        _ = outputs, kwargs
        self.events.append("chain_end")

    def on_llm_start(self, serialized: dict[str, Any] | None, prompts: list[str], **kwargs: Any) -> None:
        _ = serialized, prompts, kwargs
        self.events.append("llm_start")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        _ = response, kwargs
        self.events.append("llm_end")


def build_vector_store() -> LangChainVectorStoreAdapter:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    documents = [
        Document(
            page_content=(
                "Support archive summary: customers consistently praise the product's ease of use "
                "and the time savings it creates for small teams."
            ),
            metadata={"title": "Positive themes", "source": "memory://positive", "document_id": "doc-1"},
        ),
        Document(
            page_content=(
                "Billing complaints center on duplicate charges, invoices that are hard to interpret, "
                "and uncertainty about refund timing."
            ),
            metadata={"title": "Billing issues", "source": "memory://billing", "document_id": "doc-2"},
        ),
        Document(
            page_content=(
                "Refund-related comments mention long waits for credits to appear and inconsistent "
                "communication from support during the process."
            ),
            metadata={"title": "Refund delays", "source": "memory://refunds", "document_id": "doc-3"},
        ),
        Document(
            page_content=(
                "Some comments are too vague to action, such as 'it feels off lately' without concrete "
                "examples, dates, or workflows."
            ),
            metadata={"title": "Vague feedback", "source": "memory://vague", "document_id": "doc-4"},
        ),
        Document(
            page_content=(
                "Engineering notes: pgvector stores vector embeddings inside Postgres so applications can "
                "run semantic similarity search near the rest of their relational data."
            ),
            metadata={"title": "pgvector note", "source": "memory://pgvector", "document_id": "doc-5"},
        ),
    ]
    vector_store = InMemoryVectorStore(embeddings)
    vector_store.add_documents(documents)
    return LangChainVectorStoreAdapter(vector_store)


def build_model() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)


def ensure_env() -> str:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError("OPENAI_API_KEY is required in the environment for this probe.")
    return os.environ.get("CHECKPOINT_DB_URL", DEFAULT_CHECKPOINT_DB_URL)


def make_case(name: str, fn: Callable[[], dict[str, Any]]) -> CaseResult:
    details = fn()
    return CaseResult(name=name, passed=True, details=details)


def case_install_and_basic_run() -> dict[str, Any]:
    package_version = importlib.metadata.version("agent-search-core")
    response = advanced_rag(
        "What is pgvector and why would an application use it?",
        vector_store=build_vector_store(),
        model=build_model(),
    )
    if not response.output.strip():
        raise AssertionError("basic run returned an empty output")
    if not response.sub_items:
        raise AssertionError("basic run returned no sub-items")
    return {
        "package_version": package_version,
        "sub_item_count": len(response.sub_items),
        "final_citation_count": len(response.final_citations),
        "output_preview": response.output[:180],
    }


def case_overrides_aliases_and_callbacks() -> dict[str, Any]:
    callback = ProbeCallbackHandler()
    response = advanced_rag(
        "Summarize the customer feedback themes from the support archive.",
        vector_store=build_vector_store(),
        model=build_model(),
        rerank_enabled=False,
        query_expansion_enabled=False,
        callbacks=[callback],
        config={
            "custom-prompts": {
                "subanswer": "Answer with direct evidence and concise citations.",
            },
            "custom_prompts": {
                "subanswer": "List the major themes using only the supplied evidence.",
                "synthesis": "Produce a short executive summary grounded in the subanswers.",
            },
            "runtime_config": {
                "custom_prompts": {
                    "synthesis": "Summarize the dominant themes in 2-4 sentences with direct evidence."
                }
            },
        },
    )
    if not response.output.strip():
        raise AssertionError("override run returned an empty output")
    if not callback.events:
        raise AssertionError("callback handler observed no events")
    return {
        "callback_events": callback.events[:8],
        "sub_item_count": len(response.sub_items),
        "final_citation_count": len(response.final_citations),
        "output_preview": response.output[:180],
    }


def case_hitl_pause_and_approve_all(checkpoint_db_url: str) -> dict[str, Any]:
    question = "Summarize the customer feedback themes from the support archive."
    paused = advanced_rag(
        question,
        vector_store=build_vector_store(),
        model=build_model(),
        hitl_subquestions=True,
        checkpoint_db_url=checkpoint_db_url,
    )
    if paused.status != "paused":
        raise AssertionError(f"expected paused status, got {paused.status!r}")
    if paused.review is None or paused.review.kind != "subquestion_review":
        raise AssertionError("expected a subquestion review payload")
    resumed = advanced_rag(
        question,
        vector_store=build_vector_store(),
        model=build_model(),
        resume=paused.review.approve_all(),
        checkpoint_db_url=checkpoint_db_url,
    )
    if resumed.status != "completed" or resumed.response is None:
        raise AssertionError("approve_all resume did not complete")
    return {
        "review_kind": paused.review.kind,
        "review_item_count": len(paused.review.items),
        "output_preview": resumed.response.output[:180],
    }


def case_hitl_edit_and_reject(checkpoint_db_url: str) -> dict[str, Any]:
    question = "Summarize the customer feedback themes from the support archive."
    paused = advanced_rag(
        question,
        vector_store=build_vector_store(),
        model=build_model(),
        hitl_subquestions=True,
        checkpoint_db_url=checkpoint_db_url,
    )
    if paused.review is None:
        raise AssertionError("expected HITL review payload")
    if len(paused.review.items) < 3:
        raise AssertionError(f"expected at least 3 review items, got {len(paused.review.items)}")
    resumed = advanced_rag(
        question,
        vector_store=build_vector_store(),
        model=build_model(),
        resume=paused.review.with_decisions(
            paused.review.items[0].approve(),
            paused.review.items[1].edit("What billing and invoice problems appear most often?"),
            paused.review.items[2].reject(),
        ),
        checkpoint_db_url=checkpoint_db_url,
    )
    if resumed.status != "completed" or resumed.response is None:
        raise AssertionError("edit/reject resume did not complete")
    return {
        "review_item_count": len(paused.review.items),
        "final_sub_item_count": len(resumed.response.sub_items),
        "output_preview": resumed.response.output[:180],
    }


def case_injected_checkpointer(checkpoint_db_url: str) -> dict[str, Any]:
    question = "Summarize the customer feedback themes from the support archive."
    with PostgresSaver.from_conn_string(checkpoint_db_url) as checkpointer:
        paused = advanced_rag(
            question,
            vector_store=build_vector_store(),
            model=build_model(),
            hitl_subquestions=True,
            checkpointer=checkpointer,
        )
        if paused.status != "paused" or paused.review is None:
            raise AssertionError("checkpointer-backed HITL run did not pause")
        resumed = advanced_rag(
            question,
            vector_store=build_vector_store(),
            model=build_model(),
            resume=paused.review.approve_all(),
            checkpointer=checkpointer,
        )
    if resumed.status != "completed" or resumed.response is None:
        raise AssertionError("checkpointer-backed resume did not complete")
    return {
        "review_kind": paused.review.kind,
        "review_item_count": len(paused.review.items),
        "output_preview": resumed.response.output[:180],
    }


def case_missing_checkpoint_error() -> dict[str, Any]:
    try:
        advanced_rag(
            "Summarize the customer feedback themes from the support archive.",
            vector_store=build_vector_store(),
            model=build_model(),
            hitl_subquestions=True,
        )
    except SDKConfigurationError as exc:
        return {"error": str(exc)}
    raise AssertionError("expected SDKConfigurationError for missing checkpoint_db_url")


def case_both_checkpoint_inputs_error(checkpoint_db_url: str) -> dict[str, Any]:
    with PostgresSaver.from_conn_string(checkpoint_db_url) as checkpointer:
        try:
            advanced_rag(
                "Summarize the customer feedback themes from the support archive.",
                vector_store=build_vector_store(),
                model=build_model(),
                hitl_subquestions=True,
                checkpoint_db_url=checkpoint_db_url,
                checkpointer=checkpointer,
            )
        except SDKConfigurationError as exc:
            return {"error": str(exc)}
    raise AssertionError("expected SDKConfigurationError when both checkpoint inputs are supplied")


def main() -> None:
    checkpoint_db_url = ensure_env()
    cases = [
        make_case("install_and_basic_run", case_install_and_basic_run),
        make_case("overrides_aliases_and_callbacks", case_overrides_aliases_and_callbacks),
        make_case("hitl_pause_and_approve_all", lambda: case_hitl_pause_and_approve_all(checkpoint_db_url)),
        make_case("hitl_edit_and_reject", lambda: case_hitl_edit_and_reject(checkpoint_db_url)),
        make_case("injected_checkpointer", lambda: case_injected_checkpointer(checkpoint_db_url)),
        make_case("missing_checkpoint_error", case_missing_checkpoint_error),
        make_case("both_checkpoint_inputs_error", lambda: case_both_checkpoint_inputs_error(checkpoint_db_url)),
    ]
    print(json.dumps([asdict(case) for case in cases], indent=2))


if __name__ == "__main__":
    main()
