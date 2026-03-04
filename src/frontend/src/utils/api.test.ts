import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import { loadInternalData, runAgent, runAgentStream } from "./api";

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
        source_type: "inline",
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

  it("returns run success with final answer and progress payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse(200, {
        agent_name: "langgraph-scaffold",
        output: "Final answer",
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
      expect(result.data.sub_queries).toEqual(["q1", "q2"]);
      expect(result.data.tool_assignments).toHaveLength(2);
      expect(result.data.validation_results[0].status).toBe("validated");
      expect(result.data.graph_state?.current_step).toBe("synthesis");
    }
  });

  it("parses stream events into incremental snapshot and final payload", async () => {
    const ssePayload = [
      "event: heartbeat",
      'data: {"sequence":1,"event":"heartbeat","data":{"step":"decomposition","status":"completed","details":{}}}',
      "",
      "event: sub_queries",
      'data: {"sequence":2,"event":"sub_queries","data":{"sub_queries":["q1"]}}',
      "",
      "event: tool_assignments",
      'data: {"sequence":3,"event":"tool_assignments","data":{"tool_assignments":[{"sub_query":"q1","tool":"internal"}]}}',
      "",
      "event: validation_result",
      'data: {"sequence":4,"event":"validation_result","data":{"sub_query":"q1","tool":"internal","sufficient":true,"status":"validated","attempts":1,"follow_up_actions":[],"stop_reason":"sufficient"}}',
      "",
      "event: completed",
      'data: {"sequence":5,"event":"completed","data":{"agent_name":"langgraph-scaffold","output":"Final answer","graph_state":{"current_step":"synthesis","timeline":[{"step":"decomposition","status":"completed","details":{}}],"graph":{}}}}',
      "",
    ].join("\n");

    const fetchMock = vi.fn().mockResolvedValue(
      new Response(ssePayload, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    const snapshots: Array<{ sub_queries: string[]; output: string }> = [];

    const result = await runAgentStream(
      { query: "What changed?" },
      {
        onEvent: (_event, snapshot) => {
          snapshots.push({ sub_queries: [...snapshot.sub_queries], output: snapshot.output });
        },
      },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.sub_queries).toEqual(["q1"]);
      expect(result.data.output).toBe("Final answer");
      expect(result.data.tool_assignments).toEqual([{ sub_query: "q1", tool: "internal" }]);
      expect(result.data.validation_results).toHaveLength(1);
    }
    expect(snapshots.some((snapshot) => snapshot.sub_queries.includes("q1"))).toBe(true);
    expect(snapshots[snapshots.length - 1]?.output).toBe("Final answer");
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

  it("returns malformed response when stream payload is invalid", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        ["event: sub_queries", 'data: {"sequence":1,"event":"sub_queries","data":{"oops":true}}', ""].join("\n"),
        {
          status: 200,
          headers: { "Content-Type": "text/event-stream" },
        },
      ),
    );

    const result = await runAgentStream(
      { query: "Hello" },
      {},
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
