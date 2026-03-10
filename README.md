# agent-search

`agent-search` is a Dockerized RAG application and SDK-style runtime built with FastAPI, React, Postgres, pgvector, and a graph-stage answer pipeline.

## Runtime State Graph (Data Flow + LM Calls)

```mermaid
flowchart TD
    A[POST /api/agents/run-async] --> B[run_runtime_agent payload.query]
    B --> D[Decompose Node]
    D -->|LM call #1\nChatOpenAI structured output DecompositionPlan| E[Sub-questions list]

    E --> F{{Parallel lanes\n1 per sub-question}}
    F --> G[Expand Node]
    G -->|LM call #2 per lane\nMultiQueryRetriever.generate_queries| H[expanded_queries]
    H --> I[Search Node\nvector similarity search per query]
    I --> J[retrieved_docs + retrieval_provenance]
    J --> K[Rerank Node]
    K -->|Optional LM call #3 per lane\nOpenAI rerank provider| L[reranked_docs]
    K -->|Fallback provider| L2[Flashrank / deterministic order]
    L --> M[Answer Node]
    L2 --> M
    M -->|LM call #4 per lane\ngenerate_subanswer| N[sub_answer + citation indices]
    N --> P[Synthesize Final Node]
    P -->|LM call #5\ngenerate_final_synthesis_answer| Q[final output]
    Q --> R[stage snapshot synthesize_final]
    R --> S[RuntimeAgentRunResponse\nmain_question + sub_qa + output + final_citations]
```

## SDK Logic (In-Process)

Entry points:

- `advanced_rag(query, *, vector_store, model, config=None, callbacks=None, langfuse_callback=None)`
- `run(query, *, vector_store, model, config=None, callbacks=None, langfuse_callback=None)`
- `run_async(query, *, vector_store, model, config=None)`
- `get_run_status(job_id)`
- `cancel_run(job_id)`

Minimal usage (you must provide both a chat model and a vector store):

```python
from langchain_openai import ChatOpenAI
from agent_search import advanced_rag
from agent_search.vectorstore.langchain_adapter import LangChainVectorStoreAdapter

vector_store = LangChainVectorStoreAdapter(your_langchain_vector_store)
model = ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)

response = advanced_rag("What is pgvector?", vector_store=vector_store, model=model)
print(response.output)
```

`run(...)` remains available as a compatibility alias and delegates to `advanced_rag(...)`.

Tracing behavior for `advanced_rag(...)`:

- Pass `langfuse_callback=...` to supply an explicit callback.
- If omitted, SDK attempts to build a Langfuse callback from environment settings + sampling.

The SDK does not auto-build a model or vector store. When running the full app in this repo, the backend constructs those dependencies for API calls.

PyPI description:

- `https://pypi.org/project/agent-search-core/`
