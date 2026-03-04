import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import { listWikiSources, loadInternalData, runAgent } from "./api";

function jsonResponse(status: number, payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("frontend api client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns load success with usable counts", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        status: "success",
        source_type: "inline",
        documents_loaded: 2,
        chunks_created: 7,
      }),
    );

    const result = await loadInternalData(
      {
        documents: [
          { title: "Doc 1", content: "A" },
          { title: "Doc 2", content: "B" },
        ],
      },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.documents_loaded).toBe(2);
      expect(result.data.chunks_created).toBe(7);
    }
  });

  it("sends wiki load payload to the load endpoint", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        status: "success",
        source_type: "wiki",
        documents_loaded: 1,
        chunks_created: 5,
      }),
    );

    const payload = {
      source_type: "wiki" as const,
      wiki: {
        source_id: "strait_of_hormuz",
      },
    };
    const result = await loadInternalData(payload, { fetchImpl: fetchMock as unknown as typeof fetch });

    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/internal-data/load",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
      }),
    );
  });

  it("lists curated wiki sources with loaded state", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        sources: [
          {
            source_id: "strait_of_hormuz",
            label: "Strait of Hormuz",
            article_query: "Strait of Hormuz",
            already_loaded: false,
          },
        ],
      }),
    );

    const result = await listWikiSources({ fetchImpl: fetchMock as unknown as typeof fetch });
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/internal-data/wiki-sources",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("returns run success with final answer and progress payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        agent_name: "langgraph-scaffold",
        output: "Final answer",
        thread_id: "thread-123",
        checkpoint_id: null,
        sub_queries: ["q1", "q2"],
        tool_assignments: [
          { sub_query: "q1", tool: "internal" },
          { sub_query: "q2", tool: "web" },
        ],
        retrieval_results: [],
        validation_results: [
          {
            sub_query: "q1",
            tool: "internal",
            sufficient: true,
            status: "validated",
            attempts: 1,
            follow_up_actions: [],
            stop_reason: "sufficient",
          },
        ],
        web_tool_runs: [],
        graph_state: {
          current_step: "synthesis",
          timeline: [
            { step: "decomposition", status: "completed", details: {} },
            { step: "synthesis", status: "completed", details: {} },
          ],
          graph: {},
        },
      }),
    );

    const result = await runAgent(
      { query: "What changed?" },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.output).toBe("Final answer");
      expect(result.data.thread_id).toBe("thread-123");
      expect(result.data.checkpoint_id).toBeNull();
      expect(result.data.sub_queries).toEqual(["q1", "q2"]);
      expect(result.data.tool_assignments).toHaveLength(2);
      expect(result.data.validation_results[0].status).toBe("validated");
      expect(result.data.graph_state?.current_step).toBe("synthesis");
    }
  });

  it("accepts run payloads with internal retrieval chunk metadata", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        agent_name: "langgraph-scaffold",
        output: "Final answer",
        thread_id: "thread-123",
        checkpoint_id: null,
        sub_queries: ["q1"],
        tool_assignments: [{ sub_query: "q1", tool: "internal" }],
        retrieval_results: [
          {
            sub_query: "q1",
            tool: "internal",
            internal_results: [
              {
                chunk_id: 1,
                document_id: 2,
                document_title: "Strait of Hormuz",
                source_type: "wiki",
                source_ref: "strait_of_hormuz",
                content: "evidence",
                score: 0.88,
                chunk_metadata: {
                  source: "https://en.wikipedia.org/wiki/Strait_of_Hormuz",
                  topic: "Strait of Hormuz",
                },
              },
            ],
            web_search_results: [],
            opened_urls: [],
            opened_pages: [],
          },
        ],
        validation_results: [],
        web_tool_runs: [],
        graph_state: null,
      }),
    );

    const result = await runAgent(
      { query: "metadata check" },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result.ok).toBe(true);
  });

  it("accepts optional persistence fields in runAgent request payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        agent_name: "langgraph-scaffold",
        output: "Final answer",
        thread_id: "thread-xyz",
        checkpoint_id: "checkpoint-9",
        sub_queries: [],
        tool_assignments: [],
        retrieval_results: [],
        validation_results: [],
        web_tool_runs: [],
        graph_state: null,
      }),
    );

    const payload = {
      query: "Continue this thread",
      thread_id: "thread-xyz",
      user_id: "user-42",
      checkpoint_id: "checkpoint-9",
    };
    const result = await runAgent(payload, { fetchImpl: fetchMock as unknown as typeof fetch });

    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/agents/run",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
      }),
    );
    if (result.ok) {
      expect(result.data.thread_id).toBe("thread-xyz");
      expect(result.data.checkpoint_id).toBe("checkpoint-9");
    }
  });

  it("maps non-2xx response to deterministic safe error", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(503, { detail: "down" }));

    const result = await runAgent(
      { query: "Hello" },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result).toEqual({
      ok: false,
      error: {
        type: "http",
        message: "Request failed with status 503",
        retryable: true,
        statusCode: 503,
      },
    });
  });

  it("maps timeout failures to deterministic retryable error", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      return new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("aborted", "AbortError"));
        });
      });
    });

    const promise = runAgent(
      { query: "Hello" },
      { fetchImpl: fetchMock as unknown as typeof fetch, timeoutMs: 5 },
    );

    await vi.advanceTimersByTimeAsync(10);

    const result = await promise;
    expect(result).toEqual({
      ok: false,
      error: {
        type: "timeout",
        message: "Request timed out. Please retry.",
        retryable: true,
      },
    });
  });

  it("maps network failures to deterministic retryable error", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));

    const result = await runAgent(
      { query: "Hello" },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result).toEqual({
      ok: false,
      error: {
        type: "network",
        message: "Network error. Please check connection and retry.",
        retryable: true,
      },
    });
  });

  it("rejects malformed payload with deterministic fallback error", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        output: "Missing required fields",
      }),
    );

    const result = await runAgent(
      { query: "Hello" },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result).toEqual({
      ok: false,
      error: {
        type: "malformed_response",
        message: "Backend response did not match expected shape.",
        retryable: false,
      },
    });
  });

  it("rejects payloads missing required thread_id in run response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        agent_name: "langgraph-scaffold",
        output: "Final answer",
        checkpoint_id: null,
        sub_queries: [],
        tool_assignments: [],
        retrieval_results: [],
        validation_results: [],
        web_tool_runs: [],
        graph_state: null,
      }),
    );

    const result = await runAgent(
      { query: "Hello" },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result).toEqual({
      ok: false,
      error: {
        type: "malformed_response",
        message: "Backend response did not match expected shape.",
        retryable: false,
      },
    });
  });

  it("rejects run payloads with malformed chunk metadata", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        agent_name: "langgraph-scaffold",
        output: "Final answer",
        thread_id: "thread-123",
        checkpoint_id: null,
        sub_queries: ["q1"],
        tool_assignments: [{ sub_query: "q1", tool: "internal" }],
        retrieval_results: [
          {
            sub_query: "q1",
            tool: "internal",
            internal_results: [
              {
                chunk_id: 1,
                document_id: 2,
                document_title: "Strait of Hormuz",
                source_type: "wiki",
                source_ref: "strait_of_hormuz",
                content: "evidence",
                score: 0.88,
                chunk_metadata: {
                  source: "https://en.wikipedia.org/wiki/Strait_of_Hormuz",
                },
              },
            ],
            web_search_results: [],
            opened_urls: [],
            opened_pages: [],
          },
        ],
        validation_results: [],
        web_tool_runs: [],
        graph_state: null,
      }),
    );

    const result = await runAgent(
      { query: "metadata check" },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result).toEqual({
      ok: false,
      error: {
        type: "malformed_response",
        message: "Backend response did not match expected shape.",
        retryable: false,
      },
    });
  });
});
