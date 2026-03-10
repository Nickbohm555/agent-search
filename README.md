<p align="center">
  <img src="assets/readme-hud-banner.png" alt="agent-search banner" width="100%" data-darkreader-ignore />
</p>

# agent-search

`agent-search` is a Dockerized RAG application and SDK-style runtime built with FastAPI, React, Postgres, pgvector, and a graph-stage answer pipeline.

## Runtime State Graph (Data Flow + LM Calls)

```mermaid
flowchart TD
    A["SDK caller"] --> B["advanced_rag / run / run_async"]
    B --> C["Validate inputs<br/>model + vector_store required"]
    C --> D["Build runtime config<br/>callbacks + optional Langfuse callback"]
    D --> E["run_runtime_agent(query, deps)"]
    E --> F["Decompose Node"]
    F -->|LM call #1<br/>Structured decomposition plan| G["sub-questions list"]

    G --> SQ1["Sub-question 1"]
    G --> SQ2["Sub-question 2"]
    G --> SQ3["Sub-question 3"]
    G --> SQN["Sub-question N"]

    SQ1 --> EX1["Expand Node"]
    SQ2 --> EX2["Expand Node"]
    SQ3 --> EX3["Expand Node"]
    SQN --> EXN["Expand Node"]

    EX1 -->|LM call #2 per lane<br/>query expansion| SR1["Search Node"]
    EX2 -->|LM call #2 per lane<br/>query expansion| SR2["Search Node"]
    EX3 -->|LM call #2 per lane<br/>query expansion| SR3["Search Node"]
    EXN -->|LM call #2 per lane<br/>query expansion| SRN["Search Node"]

    SR1 --> RR1["Rerank Node"]
    SR2 --> RR2["Rerank Node"]
    SR3 --> RR3["Rerank Node"]
    SRN --> RRN["Rerank Node"]

    RR1 -->|LM call #3 per lane<br/>OpenAI rerank provider| AN1["Answer Node"]
    RR2 -->|LM call #3 per lane<br/>OpenAI rerank provider| AN2["Answer Node"]
    RR3 -->|LM call #3 per lane<br/>OpenAI rerank provider| AN3["Answer Node"]
    RRN -->|LM call #3 per lane<br/>OpenAI rerank provider| ANN["Answer Node"]

    AN1 -->|LM call #4 per lane<br/>sub-answer generation| SA1["sub-answer + citations"]
    AN2 -->|LM call #4 per lane<br/>sub-answer generation| SA2["sub-answer + citations"]
    AN3 -->|LM call #4 per lane<br/>sub-answer generation| SA3["sub-answer + citations"]
    ANN -->|LM call #4 per lane<br/>sub-answer generation| SAN["sub-answer + citations"]

    SA1 --> R["Synthesize Final Node"]
    SA2 --> R
    SA3 --> R
    SAN --> R

    R -->|LM call #5<br/>final synthesis answer| S["final output"]
    S --> T["RuntimeAgentRunResponse<br/>main_question + sub_qa + output + final_citations"]
```

### Deep Dive

#### Decompose Node

| Aspect | Details |
| --- | --- |
| How it works | Uses an LLM planner to turn the main question into atomic sub-questions, normalizes/dedupes them, and enforces a bounded count (`DECOMPOSITION_ONLY_MAX_SUBQUESTIONS`, clamped 5-10). |
| Why effective | Splits multi-hop questions into targeted retrieval tasks, improving evidence recall and reducing single-query blind spots. |
| Knobs | `DECOMPOSITION_ONLY_MODEL`, `DECOMPOSITION_ONLY_TEMPERATURE`, `DECOMPOSITION_ONLY_MAX_SUBQUESTIONS`, `DECOMPOSITION_LLM_TIMEOUT_S`. More sub-questions improve coverage but increase cost/latency. |
| Potential changes | Add adaptive decomposition count from question complexity and token budget. |

#### Expand Node

| Aspect | Details |
| --- | --- |
| How it works | Expands each sub-question into alternative phrasings and related query variants before retrieval. |
| Why effective | Improves lexical/semantic coverage so retrieval is less sensitive to wording mismatch. |
| Knobs | Expansion query count and max query length in expansion config. Higher expansion breadth helps recall but can add noisy candidates. |
| Potential changes | Add domain-aware expansion templates (for example legal, biomedical, finance). |

#### Search Node

| Aspect | Details |
| --- | --- |
| How it works | Executes similarity search for each expanded query, merges results by document identity, preserves provenance, and caps merged candidates. |
| Why effective | Multi-query retrieval plus dedupe captures more relevant evidence while limiting repeated chunks. |
| Knobs | `retrieval.search_node_k_fetch`, `retrieval.search_node_score_threshold`, `retrieval.search_node_merged_cap`. Higher `k_fetch` increases recall and latency; tighter threshold increases precision and miss risk. |
| Potential changes | Add hybrid retrieval (BM25 + vector) with learned merge weighting. |

#### Rerank Node

| Aspect | Details |
| --- | --- |
| How it works | Sends retrieved candidates to OpenAI reranking prompt, gets JSON-ordered ids with scores, and reorders evidence; applies `top_n` truncation if set. |
| Why effective | Re-optimizes ranking for the exact sub-question, usually improving top-context relevance for answer generation. |
| Knobs | `rerank.enabled`, `rerank.provider`, `rerank.top_n`, `RERANK_OPENAI_MODEL_NAME`, `RERANK_OPENAI_TEMPERATURE`, `timeout.rerank_timeout_s`. Smaller `top_n` reduces cost but can drop weak-signal evidence. |
| Potential changes | Add score fusion (`s_final = alpha*s_vec + (1-alpha)*s_rerank`) and calibrated confidence thresholds. |

#### Answer Node

| Aspect | Details |
| --- | --- |
| How it works | Generates one sub-answer per lane from reranked evidence and keeps citation index references aligned to reranked docs. |
| Why effective | Keeps claims grounded to lane-specific evidence and makes provenance explicit. |
| Knobs | Sub-answer generation/verification model settings and timeout controls (`timeout.subanswer_generation_timeout_s`, `timeout.subanswer_verification_timeout_s`). |
| Potential changes | Add stricter citation validation that rejects claims without supporting passages. |

#### Synthesize Final Node

| Aspect | Details |
| --- | --- |
| How it works | Combines all sub-answers into one final response and outputs `final_citations` mapped back to evidence rows. |
| Why effective | Produces one coherent answer while preserving traceability to per-lane evidence. |
| Knobs | Final synthesis timeout (`timeout.initial_answer_timeout_s`) and synthesis prompt/model behavior. |
| Potential changes | Add contradiction resolution and confidence scoring across lanes before final output. |

## SDK Logic (In-Process)

Before calling `advanced_rag(...)`, install `agent-search-core`, configure your model provider credentials (for example OpenAI), and provide both:
- a chat model instance
- a vector store adapter (`LangChainVectorStoreAdapter`)

```python
from langchain_openai import ChatOpenAI
from langfuse.langchain import CallbackHandler
from agent_search import advanced_rag
from agent_search.vectorstore.langchain_adapter import LangChainVectorStoreAdapter

vector_store = LangChainVectorStoreAdapter(your_langchain_vector_store)
model = ChatOpenAI(model="gpt-4.1-mini", temperature=0.0)
langfuse_callback = CallbackHandler(
    public_key="...",
    secret_key="...",
    host="https://cloud.langfuse.com",
)
response = advanced_rag(
    "What is pgvector?",
    vector_store=vector_store,
    model=model,
    langfuse_callback=langfuse_callback,
)
print(response.output)
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

### Deep Dive

| Focus | Deep dive (how it works, why effective, knobs) | Potential changes |
| --- | --- | --- |
| Setup and required inputs | You install `agent-search-core`, construct a compatible `vector_store` adapter, and pass a chat `model` into `advanced_rag(...)`. The SDK validates both inputs and rejects `None` early to prevent ambiguous runtime failures. | Add a one-call helper that builds a default model + vector store from environment for quick starts. |
| Code path | `advanced_rag(...)` resolves `RuntimeConfig`, validates vector store protocol compatibility, attaches optional callbacks, and executes `run_runtime_agent(...)`. This keeps API surface small while routing all logic through one runtime path. | Add a dry-run mode that validates config and dependencies without performing LLM/vector calls. |
| Why it is effective | The SDK uses typed request/response schemas and deterministic runtime staging, so callers get a stable output contract (`main_question`, `sub_qa`, `output`, `final_citations`) while internals can evolve without breaking integration code. | Add response version tags for explicit forward-compatibility across future schema expansions. |
| Knobs and tradeoffs | Pass `config` to tune `retrieval.*`, `rerank.*`, and `timeout.*`. Larger retrieval/rerank windows generally improve answer quality but increase latency and token usage; tighter timeouts reduce worst-case latency but increase fallback risk. | Expose prebuilt config presets plus per-stage telemetry recommendations in SDK logs. |
