<p align="center">
  <img src="assets/readme-hud-banner.png" alt="agent-search banner" width="100%" data-darkreader-ignore />
</p>

# agent-search

`agent-search` supercharges your RAG flow by improving accuracy with our open-source framework, backed by the Onyx team’s work on agentic search with LangGraph: https://onyx.app/blog/agent-search-with-langgraph?ref=blog.langchain.com.

Onyx builds AI search and knowledge experiences for teams that need dependable, source-grounded answers. Agent-search distills those production learnings into a developer SDK so you can ship more reliable retrieval flows without rebuilding the orchestration stack from scratch.

## Documentation

The consolidated project reference is available at `docs/application-document.html`. It is the agent-search-specific HTML source of truth for architecture, concerns, conventions, integrations, stack, structure, testing, runtime flow, and key tradeoffs, including the current no-timeout-guardrails runtime behavior.

Live architecture blog (GitHub Pages): [https://nickbohm555.github.io/agent-search/architecture.html](https://nickbohm555.github.io/agent-search/architecture.html).

## Data Flow Diagram

```mermaid
flowchart TD
    Q["Main question"] --> D["Decompose"]
    D --> HITL{"Subquestion HITL?"}
    HITL -->|On| REV["Review / edit subquestions"]
    HITL -->|Off| SQ["Subquestions"]
    REV --> SQ

    SQ --> S1["Subquestion 1"]
    SQ --> S2["Subquestion 2"]
    SQ --> S3["Subquestion N"]

    S1 --> QE1{"Subquery expansion?"}
    QE1 -->|On| EXP1["Expand query"]
    QE1 -->|Off| RET1["Retrieve evidence"]
    EXP1 --> RET1
    RET1 --> RR1{"Rerank?"}
    RR1 -->|On| RERANK1["Rerank results"]
    RR1 -->|Off| ANS1["Answer subquestion"]
    RERANK1 --> ANS1
    CP1["Custom prompt: subquestion answers"] -.-> ANS1
    ANS1 --> SA1["Sub-answer + citations"]

    S2 --> QE2{"Subquery expansion?"}
    QE2 -->|On| EXP2["Expand query"]
    QE2 -->|Off| RET2["Retrieve evidence"]
    EXP2 --> RET2
    RET2 --> RR2{"Rerank?"}
    RR2 -->|On| RERANK2["Rerank results"]
    RR2 -->|Off| ANS2["Answer subquestion"]
    RERANK2 --> ANS2
    CP1 -.-> ANS2
    ANS2 --> SA2["Sub-answer + citations"]

    S3 --> QE3{"Subquery expansion?"}
    QE3 -->|On| EXP3["Expand query"]
    QE3 -->|Off| RET3["Retrieve evidence"]
    EXP3 --> RET3
    RET3 --> RR3{"Rerank?"}
    RR3 -->|On| RERANK3["Rerank results"]
    RR3 -->|Off| ANS3["Answer subquestion"]
    RERANK3 --> ANS3
    CP1 -.-> ANS3
    ANS3 --> SA3["Sub-answer + citations"]

    SA1 --> SYN["Final synthesis"]
    SA2 --> SYN
    SA3 --> SYN
    CP2["Custom prompt: synthesis"] -.-> SYN
    SYN --> OUT["Final answer"]
```

## SDK Quick Reference (PyPI)

For the full, canonical SDK docs, see [https://pypi.org/project/agent-search-core/](https://pypi.org/project/agent-search-core/).

The PyPI package is an in-process Python SDK for `agent-search`. It is intentionally narrow: consumers should call `advanced_rag(...)` and treat that as the supported entrypoint. The SDK always requires both:

- A chat model (for example `langchain_openai.ChatOpenAI`)
- A vector store that implements `similarity_search(query, k, filter=None)`

It does not auto-build these dependencies for you.

**Install (PyPI)**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install agent-search-core
python -c "import agent_search; print(agent_search.__file__)"
```

**Quick Start**

```python
from langchain_openai import ChatOpenAI
from agent_search import advanced_rag
from agent_search.vectorstore.langchain_adapter import LangChainVectorStoreAdapter

vector_store = LangChainVectorStoreAdapter(your_langchain_vector_store)
model = ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)

response = advanced_rag(
    "What is pgvector?",
    vector_store=vector_store,
    model=model,
)
print(response.output)
```

**Included Features**

- Multi-step agentic retrieval: Breaks a main question into subquestions, runs retrieval across parallel lanes, and synthesizes a final answer from the collected evidence.
- Subquestion HITL review: Supports one optional human-in-the-loop checkpoint after decomposition so operators can review or edit subquestions before execution continues.
- Optional query expansion: Lets you turn query expansion on or off per run to broaden retrieval coverage when the question benefits from wider search terms.
- Optional reranking: Lets you turn reranking on or off per run to reorder retrieved evidence before subanswers are generated.
- Checkpointed resume flows: Supports resumable HITL runs through checkpoint persistence so paused work can continue without restarting the full graph.
- Flexible checkpoint ownership: Works with either an SDK-managed `checkpoint_db_url` or an injected `checkpointer`, depending on whether you want the SDK or your app to own checkpoint storage.
- Runtime controls via config: Exposes `runtime_config` and related config controls so callers can adjust runtime behavior without changing application code.
- Prompt overrides: Exposes `custom_prompts.subanswer` and `custom_prompts.synthesis` so teams can customize answer-generation behavior while preserving runtime-supplied question and evidence inputs.
- SDK-friendly pause/resume contract: Returns a normalized `review` object on pauses and uses SDK-owned resume helpers instead of requiring callers to construct raw backend payloads.
- Callback integration: Accepts LangChain-compatible callbacks so application telemetry or orchestration hooks can observe the run lifecycle.

For broader runtime and prompt behavior details, see `docs/application-document.html`.

**Example Flow**

Screenshot of the end-to-end flow with subquestion review, optional query expansion and reranking, and final synthesis.

<img src="screenshot.png" alt="Example flow screenshot showing the end-to-end agent-search runtime flow." width="100%" />
