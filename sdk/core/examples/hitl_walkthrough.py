from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sys
from typing import Any

from langgraph.types import Command
from schemas import RuntimeAgentRunResponse, SubQuestionAnswer

try:
    from agent_search import advanced_rag
    from agent_search import public_api as public_api_module
except ImportError:
    PACKAGE_ROOT = Path(__file__).resolve().parents[1]
    SRC_ROOT = PACKAGE_ROOT / "src"
    if str(SRC_ROOT) not in sys.path:
        sys.path.insert(0, str(SRC_ROOT))
    from agent_search import advanced_rag
    from agent_search import public_api as public_api_module


class DemoVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        _ = query, k, filter
        return []


class DemoGraph:
    def __init__(self) -> None:
        self._subquestions = [
            "What are the strongest positive themes?",
            "What billing complaints appear repeatedly?",
            "Which comments are too vague to action?",
        ]

    def stream(self, graph_input: Any, *, config: dict[str, Any], stream_mode: list[str]):
        _ = stream_mode
        configurable = config["configurable"]
        thread_id = str(configurable.get("thread_id") or configurable.get("checkpoint_id"))
        resume_payload = graph_input.resume if isinstance(graph_input, Command) else None

        if resume_payload is None:
            yield (
                "checkpoints",
                {"config": {"configurable": {"checkpoint_id": thread_id}}},
            )
            yield (
                "updates",
                {
                    "__interrupt__": [
                        type(
                            "Interrupt",
                            (),
                            {
                                "value": {
                                    "kind": "subquestion_review",
                                    "stage": "subquestions_ready",
                                    "checkpoint_id": thread_id,
                                    "subquestions": [
                                        {
                                            "subquestion_id": f"sq-{index + 1}",
                                            "sub_question": text,
                                            "index": index,
                                        }
                                        for index, text in enumerate(self._subquestions)
                                    ],
                                }
                            },
                        )()
                    ]
                },
            )
            return

        if hasattr(resume_payload, "decisions") and resume_payload.decisions and hasattr(
            resume_payload.decisions[0], "subquestion_id"
        ):
            updated_subquestions: list[str] = []
            decisions_by_id = {decision.subquestion_id: decision for decision in resume_payload.decisions}
            for index, text in enumerate(self._subquestions):
                decision = decisions_by_id.get(f"sq-{index + 1}")
                if decision is None or decision.action == "approve":
                    updated_subquestions.append(text)
                    continue
                if decision.action == "edit" and decision.edited_text:
                    updated_subquestions.append(decision.edited_text)
                    continue
                if decision.action == "deny":
                    continue
            self._subquestions = updated_subquestions

        if resume_payload is not None and not hasattr(resume_payload, "decisions"):
            raise RuntimeError("DemoGraph expected a subquestion decision payload for resume.")

        if resume_payload is not None:
            yield (
                "checkpoints",
                {"config": {"configurable": {"checkpoint_id": thread_id}}},
            )

        yield (
            "values",
            {
                "main_question": "Summarize the customer feedback themes from the support archive.",
                "run_metadata": type("RunMetadata", (), {"thread_id": thread_id})(),
                "sub_qa": [
                    SubQuestionAnswer(
                        sub_question=subquestion,
                        sub_answer="Resolved using the reviewed subquestion set.",
                    )
                    for subquestion in self._subquestions
                ],
                "output": "Customer feedback clusters around product value, billing friction, and refund delays.",
            },
        )

    def invoke(self, graph_input: Any, *, config: dict[str, Any]):
        values = list(self.stream(graph_input, config=config, stream_mode=["values"]))
        if not values:
            raise RuntimeError("DemoGraph.invoke expected terminal values.")
        return values[-1][1]


_DEMO_GRAPH: DemoGraph | None = None


@contextmanager
def fake_compile_graph_with_checkpointer(_builder: Any, **_kwargs: Any):
    if _DEMO_GRAPH is None:
        raise RuntimeError("Demo graph must be initialized before running the walkthrough.")
    yield _DEMO_GRAPH


def fake_map_graph_state_to_runtime_response(state: dict[str, Any]) -> RuntimeAgentRunResponse:
    return RuntimeAgentRunResponse(
        main_question=state["main_question"],
        thread_id=state["run_metadata"].thread_id,
        sub_items=[(item.sub_question, item.sub_answer) for item in state["sub_qa"]],
        output=state["output"],
    )


def main() -> None:
    global _DEMO_GRAPH
    _DEMO_GRAPH = DemoGraph()
    public_api_module.compile_graph_with_checkpointer = fake_compile_graph_with_checkpointer
    public_api_module.legacy_service.map_graph_state_to_runtime_response = fake_map_graph_state_to_runtime_response

    vector_store = DemoVectorStore()
    model = object()
    question = "Summarize the customer feedback themes from the support archive."
    thread_id = "550e8400-e29b-41d4-a716-446655440230"

    first = advanced_rag(
        question,
        vector_store=vector_store,
        model=model,
        hitl_subquestions=True,
        config={"thread_id": thread_id},
        checkpoint_db_url="postgresql+psycopg://agent_user:agent_pass@localhost:5432/agent_search",
    )
    assert first.status == "paused"
    assert first.review is not None
    assert first.review.kind == "subquestion_review"
    print("First pause:", first.review.kind)
    for item in first.review.items:
        print(f"  {item.item_id}: {item.text}")

    second = advanced_rag(
        question,
        vector_store=vector_store,
        model=model,
        resume=first.review.with_decisions(
            first.review.items[0].approve(),
            first.review.items[1].edit("What billing and invoice complaints appear repeatedly?"),
            first.review.items[2].reject(),
        ),
        checkpoint_db_url="postgresql+psycopg://agent_user:agent_pass@localhost:5432/agent_search",
    )
    assert second.status == "completed"
    assert second.response is not None
    print("Final status:", second.status)
    print("Final output:", second.response.output)
    for sub_question, sub_answer in second.response.sub_items:
        print(f"  {sub_question} -> {sub_answer}")


if __name__ == "__main__":
    main()
