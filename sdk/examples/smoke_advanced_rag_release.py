from __future__ import annotations

from agent_search import advanced_rag
from agent_search import public_api
from schemas import RuntimeAgentRunResponse


class CompatibleVectorStore:
    def similarity_search(self, query: str, k: int, filter=None) -> list[object]:
        return []


def fake_run_runtime_agent(payload, *, model, vector_store, callbacks=None, langfuse_callback=None):
    assert payload.query == "Does the installed SDK expose advanced_rag?"
    assert model is not None
    assert vector_store is not None
    assert callbacks is None
    assert langfuse_callback is None
    return RuntimeAgentRunResponse(
        main_question=payload.query,
        thread_id=payload.thread_id or "smoke-thread",
        sub_items=[("Does the installed SDK expose advanced_rag?", "Yes.")],
        output="advanced_rag smoke test passed.",
    )


public_api.run_runtime_agent = fake_run_runtime_agent

response = advanced_rag(
    "Does the installed SDK expose advanced_rag?",
    vector_store=CompatibleVectorStore(),
    model=object(),
)

assert response.output == "advanced_rag smoke test passed."
print(response.output)
