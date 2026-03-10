<p align="center">
  <img src="assets/readme-hud-banner.png" alt="agent-search banner" width="100%" data-darkreader-ignore />
</p>

# agent-search

`agent-search` is a Dockerized RAG application and SDK-style runtime built with FastAPI, React, Postgres, pgvector, and a graph-stage answer pipeline.

## Tech Stack

- Backend: FastAPI + Python + LangChain runtime nodes
- Frontend: React + TypeScript + Vite
- Database: Postgres + pgvector
- Packaging/runtime: Docker Compose
- SDK/deps: `agent-search-core`, `uv` for Python dependency management
- Model/RAG components: chat model + vector store adapter + LLM reranker

## Architecture Decisions

This architecture was inspired by LangChain's write-up on agent search with LangGraph:
- `https://blog.langchain.com/beyond-rag-implementing-agent-search-with-langgraph-for-smarter-knowledge-retrieval/`

Why this approach was effective for this project:
- It maps complex retrieval into explicit node stages with clear dependencies, which makes behavior easier to reason about than a single monolithic RAG prompt.
- It supports fan-out parallel sub-question processing, which improves coverage on ambiguous or multi-entity queries while keeping latency practical.
- It keeps the pipeline extensible: decomposition, expansion, retrieval, reranking, answering, and synthesis can evolve independently without rewriting the whole runtime.

Why this project took inspiration from it:
- The problem profile is similar: broad, ambiguous questions where vanilla single-query retrieval often misses key evidence.
- A graph-style execution model fits the need for traceability, stage-level observability, and controlled fallbacks when a lane has weak evidence.

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

## SDK Logic

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

## Runtime Node Summary

| Node | Input -> Output | How it works (beginner-friendly) | Why effective / what is needed |
| --- | --- | --- | --- |
| `Decompose` | **Input:** main user question (+ optional initial context)<br/>**Output:** list of sub-questions | **What it does:** Calls a structured-output LangChain LLM (`DecompositionPlan`) in `run_decomposition_node(...)`.<br/>**Core logic:** Cleans text, removes duplicates, and caps count so downstream work stays controlled. | **Why it helps:** Large questions become smaller tasks that are easier to retrieve evidence for.<br/>**Needs:** chat model, decomposition prompt/config, runtime metadata. |
| `Expand` | **Input:** one sub-question<br/>**Output:** expanded query list | **What it does:** Uses `MultiQueryRetriever.from_llm(...)` in `expand_queries_for_subquestion(...)` to produce alternate phrasings.<br/>**Core logic:** Keeps original query, normalizes/truncates, dedupes, and limits by `max_queries`. | **Why it helps:** Different phrasings find different chunks, which improves retrieval coverage.<br/>**Needs:** chat model or API key, query expansion config (`model`, `temperature`, `max_queries`, `max_query_length`). |
| `Search` | **Input:** sub-question + expanded queries + vector store<br/>**Output:** retrieved docs + provenance + citation map | **What it does:** Runs `search_documents_for_queries(...)`, which calls `search_documents_for_context(...)` per query.<br/>**Library behavior:** Uses `similarity_search_with_relevance_scores(...)` if available; otherwise `similarity_search(...)`.<br/>**Core logic:** Merges duplicate docs by identity and keeps provenance for traceability. | **Why it helps:** High-recall candidate gathering while avoiding duplicate evidence rows.<br/>**Needs:** compatible vector store adapter, embeddings-backed index, retrieval limits (`k_fetch`, thresholds, merged cap). |
| `Rerank` | **Input:** candidate docs for one sub-question<br/>**Output:** reordered docs (with updated ranks/citations) | **What it does:** `run_rerank_node(...)` calls `rerank_documents(...)` from reranker service.<br/>**Core logic:** LLM reranker receives query + passages, returns strict JSON order/scores, then runtime rewrites citation order for downstream answering. | **Why it helps:** Retrieval is broad; rerank makes top context more relevant before generation.<br/>**Needs:** rerank provider/model config and working provider credentials (OpenAI in current setup). |
| `Answer` | **Input:** one sub-question + reranked docs<br/>**Output:** sub-answer + citation indices + answerability status | **What it does:** `run_answer_node(...)` generates sub-answer text from reranked context.<br/>**Core logic:** Extracts citation markers like `[1]`, verifies they map to available citation rows, and returns guarded fallback if support is missing. | **Why it helps:** Keeps per-lane answers grounded to evidence instead of free-form output.<br/>**Needs:** answer generation model access and citation row map from previous stages. |
| `Synthesize Final` | **Input:** main question + all lane sub-answers/artifacts<br/>**Output:** final answer | **What it does:** `run_synthesize_node(...)` combines lane answers into one response.<br/>**Core logic:** Enforces final citation contract; if citations are missing/invalid, falls back to citation-valid content. | **Why it helps:** Produces a coherent top-level response while preserving provenance guarantees.<br/>**Needs:** complete sub-qa set, artifacts/citation rows, synthesis model call. |
| `Parallel lane execution` | **Input:** list of sub-questions/lane tasks<br/>**Output:** completed lane artifacts merged back into graph state | **What it does:** Runs lane work concurrently with `ThreadPoolExecutor` + `as_completed` in `run_parallel_graph_runner(...)` and timeout-aware helpers.<br/>**How it works with graphs:** All lanes follow the same node sequence; each lane keeps its own artifacts, then the graph joins lanes at synthesis. | **Why it helps:** Keeps multi-step quality benefits of decomposition without serially waiting on every lane.<br/>**Needs:** worker limit config, timeout/fallback strategy, deterministic lane merge behavior. |
