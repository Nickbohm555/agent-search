<p align="center">
  <img src="assets/readme-hud-banner.png" alt="agent-search banner" width="100%" data-darkreader-ignore />
</p>

# agent-search

`agent-search` is a Dockerized RAG application and SDK-style runtime built with FastAPI, React, Postgres, pgvector, and a graph-stage answer pipeline.

## Runtime State Graph (Data Flow + LM Calls)

```mermaid
flowchart TD
    A[SDK caller] --> B[advanced_rag / run / run_async]
    B --> C[Validate inputs\nmodel + vector_store required]
    C --> D[Build runtime config\ncallbacks + optional Langfuse]
    D --> E[run_runtime_agent(query, deps)]
    E --> F[Decompose Node]
    F -->|LM call #1\nStructured decomposition plan| G[sub-questions]

    G --> H{{Parallel lanes\n1 per sub-question}}
    H --> I[Expand Node]
    I -->|LM call #2 per lane\nquery expansion| J[expanded queries]
    J --> K[Search Node\nvector similarity retrieval]
    K --> L[retrieved docs + provenance]
    L --> M[Rerank Node]
    M -->|Optional LM call #3 per lane\nLLM rerank provider| N[reranked docs]
    M -->|Fallback provider| O[deterministic/Flashrank order]
    N --> P[Answer Node]
    O --> P
    P -->|LM call #4 per lane\nsub-answer generation| Q[sub_answer + citation indices]
    Q --> R[Synthesize Final Node]
    R -->|LM call #5\nfinal synthesis answer| S[final output]
    S --> T[RuntimeAgentRunResponse\nmain_question + sub_qa + output + final_citations]
```

## SDK Logic (In-Process)

Entry points:

- `advanced_rag(query, *, vector_store, model, config=None, callbacks=None, langfuse_callback=None, langfuse_settings=None)`
- `run(query, *, vector_store, model, config=None, callbacks=None, langfuse_callback=None, langfuse_settings=None)`
- `run_async(query, *, vector_store, model, config=None)`
- `get_run_status(job_id)`
- `cancel_run(job_id)`

Minimal usage (you must provide both a chat model and a vector store):

```python
from langchain_openai import ChatOpenAI
from agent_search import advanced_rag, build_langfuse_callback
from agent_search.vectorstore.langchain_adapter import LangChainVectorStoreAdapter

vector_store = LangChainVectorStoreAdapter(your_langchain_vector_store)
model = ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)

langfuse_callback = build_langfuse_callback(sampling_key="customer-123")
response = advanced_rag(
    "What is pgvector?",
    vector_store=vector_store,
    model=model,
    langfuse_callback=langfuse_callback,
)
print(response.output)
```

`run(...)` remains available as a compatibility alias and delegates to `advanced_rag(...)`.

Tracing behavior for `advanced_rag(...)`:

- Pass `langfuse_callback=...` to supply an explicit callback.
- Or pass `langfuse_settings={...}` and SDK builds the callback from that config.
- If both are omitted, SDK does not trace the run.

Config-driven tracing example:

```python
response = advanced_rag(
    "What is pgvector?",
    vector_store=vector_store,
    model=model,
    langfuse_settings={
        "enabled": True,
        "public_key": "...",
        "secret_key": "...",
        "host": "https://cloud.langfuse.com",
        "environment": "production",
        "release": "agent-search-core-0.1.8",
        "runtime_sample_rate": 1.0,
    },
)
```

Output schema for `advanced_rag(...)`:

```python
RuntimeAgentRunResponse(
  main_question: str,
  sub_qa: list[SubQuestionAnswer],
  output: str,
  final_citations: list[CitationSourceRow],
)
```

The SDK does not auto-build a model or vector store. When running the full app in this repo, the backend constructs those dependencies for API calls.

PyPI description:

- `https://pypi.org/project/agent-search-core/`
