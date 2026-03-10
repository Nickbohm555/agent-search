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

All code blocks in this deep-dive section are repo-derived snippets (lifted/adapted from files in `src/backend/agent_search/runtime/nodes/` and `src/backend/services/`) and trimmed for readability.

#### Decompose Node

| Field | Details |
| --- | --- |
| Input schema | `DecomposeNodeInput { main_question: str, run_metadata: GraphRunMetadata, initial_search_context: list[dict[str, Any]] }` |
| Output schema | `DecomposeNodeOutput { decomposition_sub_questions: list[str] }` |
| How it works | `run_decomposition_node(...)` calls a structured-output LLM plan, normalizes/dedupes questions, and clamps count to the configured max. |
| Reasoning math | `Q_sub = clip_K(dedupe(norm(parse(LLM(main_question, context)))))` where `K = DECOMPOSITION_ONLY_MAX_SUBQUESTIONS`. |
| Why effective | Converts one broad task into atomic retrieval tasks, which raises recall for multi-hop questions. |
| Knobs | `DECOMPOSITION_ONLY_MODEL`, `DECOMPOSITION_ONLY_TEMPERATURE`, `DECOMPOSITION_ONLY_MAX_SUBQUESTIONS`, `DECOMPOSITION_LLM_TIMEOUT_S`. |
| Potential changes | Adaptive sub-question count from query complexity and token budget. |

<details>
<summary>Orchestration snippet</summary>

```python
from agent_search.runtime.nodes.decompose import run_decomposition_node
from schemas import DecomposeNodeInput, GraphRunMetadata

output = run_decomposition_node(
    node_input=DecomposeNodeInput(
        main_question="How does pgvector indexing affect recall and latency?",
        initial_search_context=[],
        run_metadata=GraphRunMetadata(run_id="run-1"),
    ),
    model=model,
)
print(output.decomposition_sub_questions)
```

</details>

<details>
<summary>Logic snippet (repo-derived)</summary>

```python
# Based on _parse_decomposition_output(...) in runtime/nodes/decompose.py
normalized, seen = [], set()
for candidate in candidates:
    sq = normalize_sub_question(candidate)
    if not sq:
        continue
    key = sq.casefold()
    if key in seen:
        continue
    normalized.append(sq)
    seen.add(key)
decomposition_sub_questions = normalized[:max_subquestions]
```

</details>

#### Expand Node

| Field | Details |
| --- | --- |
| Input schema | `ExpandNodeInput { main_question: str, sub_question: str, run_metadata: GraphRunMetadata }` |
| Output schema | `ExpandNodeOutput { expanded_queries: list[str] }` |
| How it works | `run_expansion_node(...)` generates alternate phrasings for each sub-question via the query expansion service. |
| Query expansion internals | `expand_queries_for_subquestion(...)` normalizes whitespace, truncates by `max_query_length`, dedupes case-insensitively, always preserves original sub-question, and caps to `max_queries`. On model/API failure it falls back to `[normalized_sub_question]`. |
| Reasoning math | `E = clip_M(dedupe(norm([q] + LLM_variants(q))))`, where `M = QUERY_EXPANSION_MAX_QUERIES`. |
| Why effective | Reduces wording mismatch between question phrasing and chunk text. |
| Knobs | `QUERY_EXPANSION_MODEL`, `QUERY_EXPANSION_TEMPERATURE`, `QUERY_EXPANSION_MAX_QUERIES`, `QUERY_EXPANSION_MAX_QUERY_LENGTH`. |
| Potential changes | Domain-specific expansions and synonym lexicons. |

<details>
<summary>Orchestration snippet</summary>

```python
from agent_search.runtime.nodes.expand import run_expansion_node
from schemas import ExpandNodeInput, GraphRunMetadata

expanded = run_expansion_node(
    node_input=ExpandNodeInput(
        main_question="How does pgvector indexing affect recall and latency?",
        sub_question="What index types does pgvector support?",
        run_metadata=GraphRunMetadata(run_id="run-1"),
    ),
    model=model,
)
print(expanded.expanded_queries)
```

</details>

<details>
<summary>Logic snippet (repo-derived)</summary>

```python
# Based on _normalize_query_candidates(...) in services/query_expansion_service.py
normalized, seen = [], set()
for candidate in [original_query, *generated_queries]:
    q = normalize_query(candidate, max_query_length=max_len)
    if not q:
        continue
    key = q.casefold()
    if key in seen:
        continue
    normalized.append(q)
    seen.add(key)
    if len(normalized) >= max_queries:
        break
expanded_queries = normalized or [normalize_query(original_query, max_query_length=max_len)]
```

</details>

#### Search Node (Similarity Retrieval)

| Field | Details |
| --- | --- |
| Input schema | `SearchNodeInput { sub_question: str, expanded_queries: list[str], run_metadata: GraphRunMetadata }` |
| Output schema | `SearchNodeOutput { retrieved_docs: list[CitationSourceRow], retrieval_provenance: list[dict[str, Any]], citation_rows_by_index: dict[int, CitationSourceRow] }` |
| How it works | `run_search_node(...)` runs similarity search per normalized query, merges duplicate documents, keeps best observed score, and applies a merged cap. |
| Math reasoning | Typical embedding similarity uses cosine: `sim(q,d) = (q·d) / (||q|| ||d||)`. Multi-query retrieval approximates `score(d) = max_i sim(q_i, d)` before downstream rerank. |
| Why effective | Expansion + max-over-queries improves chance that at least one phrasing retrieves the right chunk. |
| Knobs | `retrieval.search_node_k_fetch`, `retrieval.search_node_score_threshold`, `retrieval.search_node_merged_cap`. |
| Potential changes | Hybrid ranking: `score = alpha * vector_score + (1 - alpha) * bm25_score`. |

<details>
<summary>Orchestration snippet</summary>

```python
from agent_search.runtime.nodes.search import run_search_node
from schemas import SearchNodeInput, GraphRunMetadata

searched = run_search_node(
    node_input=SearchNodeInput(
        sub_question="What index types does pgvector support?",
        expanded_queries=["pgvector index types", "ivfflat vs hnsw pgvector"],
        run_metadata=GraphRunMetadata(run_id="run-1"),
    ),
    vector_store=vector_store,
)
print(len(searched.retrieved_docs))
```

</details>

<details>
<summary>Logic snippet (repo-derived)</summary>

```python
# Based on run_search_node(...) in runtime/nodes/search.py
docs_by_query = search_documents_for_queries(vector_store=store, queries=normalized_queries, k=k_fetch)
merged_rows, seen = [], {}
for query in normalized_queries:
    for doc in docs_by_query.get(query, []):
        row = build_citation_row(doc)
        identity = build_document_identity(row.document_id, row.source, row.content)
        if identity in seen:
            idx = seen[identity]
            merged_rows[idx].score = max_nullable(merged_rows[idx].score, row.score)
            continue
        seen[identity] = len(merged_rows)
        merged_rows.append(row)
retrieved_docs = merged_rows[:merged_cap]
```

</details>

#### Rerank Node

| Field | Details |
| --- | --- |
| Input schema | `RerankNodeInput { sub_question: str, expanded_query: str, retrieved_docs: list[CitationSourceRow], run_metadata: GraphRunMetadata }` |
| Output schema | `RerankNodeOutput { reranked_docs: list[CitationSourceRow], citation_rows_by_index: dict[int, CitationSourceRow] }` |
| How it works | `run_rerank_node(...)` calls reranker with the sub-question and candidates, receives a strict JSON ranking, and rewrites evidence order + citation indices. |
| Math reasoning | Rerank estimates relevance per candidate (`s_rerank in [0,1]`) and sorts descending. If fused with retrieval score: `s_final = alpha*s_vec + (1-alpha)*s_rerank`; final rank is `argsort(s_final)`. |
| Why effective | Retrieval is high-recall; rerank is high-precision for top context used by generation. |
| Knobs | `rerank.enabled`, `rerank.provider`, `rerank.top_n`, `RERANK_OPENAI_MODEL_NAME`, `RERANK_OPENAI_TEMPERATURE`, `timeout.rerank_timeout_s`. |
| Potential changes | Add calibrated cutoff to drop low-confidence candidates before answer generation. |

<details>
<summary>Orchestration snippet</summary>

```python
from agent_search.runtime.nodes.rerank import run_rerank_node
from schemas import RerankNodeInput, GraphRunMetadata

reranked = run_rerank_node(
    node_input=RerankNodeInput(
        sub_question="What index types does pgvector support?",
        expanded_query="pgvector index types",
        retrieved_docs=searched.retrieved_docs,
        run_metadata=GraphRunMetadata(run_id="run-1"),
    )
)
print([row.score for row in reranked.reranked_docs[:3]])
```

</details>

<details>
<summary>Logic snippet (repo-derived)</summary>

```python
# Based on run_rerank_node(...) + services/reranker_service.py
rerank_query = (expanded_query or "").strip() or sub_question
ordered = rerank_documents(query=rerank_query, documents=to_retrieved_documents(retrieved_docs), config=config)
reranked_docs = []
for new_rank, item in enumerate(ordered, start=1):
    reranked_docs.append(CitationSourceRow(rank=new_rank, citation_index=new_rank, score=item.score, ...))
reranked_docs = reranked_docs[:top_n] if top_n else reranked_docs
```

</details>

#### Answer Node

| Field | Details |
| --- | --- |
| Input schema | `AnswerSubquestionNodeInput { sub_question: str, reranked_docs: list[CitationSourceRow], citation_rows_by_index: dict[int, CitationSourceRow], run_metadata: GraphRunMetadata }` |
| Output schema | `AnswerSubquestionNodeOutput { sub_answer: str, citation_indices_used: list[int], answerable: bool, verification_reason: str, citation_rows_by_index: dict[int, CitationSourceRow] }` |
| How it works | `run_answer_node(...)` generates one sub-answer from reranked evidence, extracts citation markers like `[1]`, and validates they map to available rows. |
| Reasoning math | `answerable = (|C_used| > 0) AND (C_used subseteq C_available)`, where `C_used` is citation indices extracted from generated text. |
| Why effective | Enforces citation-supported answers per lane instead of unconstrained generation. |
| Knobs | Generation model + `timeout.subanswer_generation_timeout_s`, `timeout.subanswer_verification_timeout_s`. |
| Potential changes | Add passage-level quote extraction for stricter evidence binding. |

<details>
<summary>Orchestration snippet</summary>

```python
from agent_search.runtime.nodes.answer import run_answer_node
from schemas import AnswerSubquestionNodeInput, GraphRunMetadata

subanswer = run_answer_node(
    node_input=AnswerSubquestionNodeInput(
        sub_question="What index types does pgvector support?",
        reranked_docs=reranked.reranked_docs,
        citation_rows_by_index=reranked.citation_rows_by_index,
        run_metadata=GraphRunMetadata(run_id="run-1"),
    ),
    callbacks=[],
)
print(subanswer.sub_answer, subanswer.citation_indices_used)
```

</details>

<details>
<summary>Logic snippet (repo-derived)</summary>

```python
# Based on run_answer_node(...) in runtime/nodes/answer.py
generated = generate_subanswer(sub_question=sub_question, reranked_retrieved_output=formatted_docs)
citation_indices_used = extract_citation_indices(generated)
invalid = [i for i in citation_indices_used if i not in citation_rows_by_index]
if not citation_indices_used:
    return fallback("missing_citation_markers")
if invalid:
    return fallback("missing_supporting_source_rows")
return supported_answer(generated, citation_indices_used)
```

</details>

#### Synthesize Final Node

| Field | Details |
| --- | --- |
| Input schema | `SynthesizeFinalNodeInput { main_question: str, sub_qa: list[SubQuestionAnswer], sub_question_artifacts: list[SubQuestionArtifacts], run_metadata: GraphRunMetadata }` |
| Output schema | `SynthesizeFinalNodeOutput { final_answer: str }` |
| How it works | `run_synthesize_node(...)` composes sub-answers into a final response and enforces a final citation contract (fallback if citations are missing/invalid). |
| Reasoning math | `A_final = synth(main_question, sub_qa)` then enforce `C_final subseteq C_available`; otherwise fallback to citation-valid sub-answers. |
| Why effective | Produces one coherent answer while preserving lane-level provenance constraints. |
| Knobs | Final synthesis model + `timeout.initial_answer_timeout_s`. |
| Potential changes | Add contradiction detection and confidence scoring across sub-answers. |

<details>
<summary>Orchestration snippet</summary>

```python
from agent_search.runtime.nodes.synthesize import run_synthesize_node
from schemas import SynthesizeFinalNodeInput, GraphRunMetadata

final = run_synthesize_node(
    node_input=SynthesizeFinalNodeInput(
        main_question="How does pgvector indexing affect recall and latency?",
        sub_qa=sub_qa,
        sub_question_artifacts=sub_question_artifacts,
        run_metadata=GraphRunMetadata(run_id="run-1"),
    )
)
print(final.final_answer)
```

</details>

<details>
<summary>Logic snippet (repo-derived)</summary>

```python
# Based on _enforce_final_synthesis_citation_contract(...) in runtime/nodes/synthesize.py
generated_final = generate_final_synthesis_answer(main_question=main_question, sub_qa=sub_qa)
used = extract_citation_indices(generated_final)
available = collect_available_citation_indices(sub_question_artifacts)
if not used or any(idx not in available for idx in used):
    final_answer = build_final_synthesis_citation_fallback(sub_qa=sub_qa, available_indices=available)
else:
    final_answer = generated_final
```

</details>

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
