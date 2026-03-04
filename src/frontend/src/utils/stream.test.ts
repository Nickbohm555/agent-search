import { describe, expect, it, vi } from "vitest";

import { streamAgentRun } from "./stream";

function sseFrame(payload: unknown): string {
  return `data: ${JSON.stringify(payload)}\n\n`;
}

function eventStreamResponse(frames: string[], status = 200): Response {
  const encoder = new TextEncoder();

  return new Response(
    new ReadableStream<Uint8Array>({
      start(controller) {
        for (const frame of frames) {
          controller.enqueue(encoder.encode(frame));
        }
        controller.close();
      },
    }),
    {
      status,
      headers: { "Content-Type": "text/event-stream" },
    },
  );
}

describe("frontend streaming api client", () => {
  it("parses supported stream events including retrieval_result/validation_result in order", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      eventStreamResponse([
        sseFrame({ sequence: 1, event: "heartbeat", data: { status: "started", query: "q" } }),
        sseFrame({ sequence: 2, event: "progress", data: { step: "invoke", status: "running" } }),
        sseFrame({ sequence: 3, event: "sub_queries", data: { sub_queries: ["q1"], count: 1 } }),
        sseFrame({
          sequence: 4,
          event: "tool_assignments",
          data: { tool_assignments: [{ sub_query: "q1", tool: "internal" }], count: 1 },
        }),
        sseFrame({
          sequence: 5,
          event: "retrieval_result",
          data: {
            sub_query: "q1",
            tool: "internal",
            internal_results: [],
            web_search_results: [],
            opened_urls: [],
            opened_pages: [],
          },
        }),
        sseFrame({
          sequence: 6,
          event: "validation_result",
          data: {
            sub_query: "q1",
            tool: "internal",
            sufficient: true,
            status: "validated",
            attempts: 1,
            follow_up_actions: [],
            stop_reason: "sufficient",
          },
        }),
        sseFrame({
          sequence: 7,
          event: "completed",
          data: {
            agent_name: "langgraph-scaffold",
            output: "Final",
            thread_id: "thread-1",
            checkpoint_id: null,
            sub_queries: ["q1"],
            tool_assignments: [{ sub_query: "q1", tool: "internal" }],
          },
        }),
      ]),
    );

    const received: string[] = [];
    const result = await streamAgentRun(
      { query: "Hello" },
      {
        fetchImpl: fetchMock as unknown as typeof fetch,
        onEvent: (event) => {
          received.push(event.event);
        },
      },
    );

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.completed.output).toBe("Final");
      expect(result.data.events).toHaveLength(7);
      expect(received).toEqual([
        "heartbeat",
        "progress",
        "sub_queries",
        "tool_assignments",
        "retrieval_result",
        "validation_result",
        "completed",
      ]);
    }
  });

  it("returns deterministic malformed error for invalid event payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      eventStreamResponse([
        sseFrame({ sequence: 1, event: "heartbeat", data: { status: "started", query: "q" } }),
        "data: not-json\n\n",
      ]),
    );

    const result = await streamAgentRun(
      { query: "Hello" },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result).toEqual({
      ok: false,
      error: {
        type: "malformed_response",
        message: "Stream event payload was not valid JSON.",
        retryable: false,
      },
    });
  });

  it("returns deterministic malformed error for invalid event ordering", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      eventStreamResponse([
        sseFrame({ sequence: 1, event: "heartbeat", data: { status: "started", query: "q" } }),
        sseFrame({
          sequence: 2,
          event: "tool_assignments",
          data: { tool_assignments: [{ sub_query: "q1", tool: "internal" }], count: 1 },
        }),
      ]),
    );

    const result = await streamAgentRun(
      { query: "Hello" },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result).toEqual({
      ok: false,
      error: {
        type: "malformed_response",
        message: "tool_assignments event arrived before sub_queries.",
        retryable: false,
      },
    });
  });

  it("returns deterministic malformed error when completed arrives before tool_assignments", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      eventStreamResponse([
        sseFrame({ sequence: 1, event: "heartbeat", data: { status: "started", query: "q" } }),
        sseFrame({ sequence: 2, event: "sub_queries", data: { sub_queries: ["q1"], count: 1 } }),
        sseFrame({
          sequence: 3,
          event: "completed",
          data: {
            agent_name: "langgraph-scaffold",
            output: "Final",
            thread_id: "thread-1",
            checkpoint_id: null,
            sub_queries: ["q1"],
            tool_assignments: [{ sub_query: "q1", tool: "internal" }],
          },
        }),
      ]),
    );

    const result = await streamAgentRun(
      { query: "Hello" },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result).toEqual({
      ok: false,
      error: {
        type: "malformed_response",
        message: "Completed event arrived before tool_assignments.",
        retryable: false,
      },
    });
  });

  it("maps interrupted stream without completed event to retryable user-facing error", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      eventStreamResponse([
        sseFrame({ sequence: 1, event: "heartbeat", data: { status: "started", query: "q" } }),
        sseFrame({ sequence: 2, event: "sub_queries", data: { sub_queries: ["q1"], count: 1 } }),
        sseFrame({
          sequence: 3,
          event: "tool_assignments",
          data: { tool_assignments: [{ sub_query: "q1", tool: "internal" }], count: 1 },
        }),
      ]),
    );

    const result = await streamAgentRun(
      { query: "Hello" },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result).toEqual({
      ok: false,
      error: {
        type: "network",
        message: "Stream interrupted before completion. Please retry.",
        retryable: true,
      },
    });
  });

  it("returns runtime error when backend emits structured error event", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      eventStreamResponse([
        sseFrame({ sequence: 1, event: "heartbeat", data: { status: "started", query: "q" } }),
        sseFrame({ sequence: 2, event: "error", data: { message: "runtime failed", retryable: false } }),
      ]),
    );

    const result = await streamAgentRun(
      { query: "Hello" },
      { fetchImpl: fetchMock as unknown as typeof fetch },
    );

    expect(result).toEqual({
      ok: false,
      error: {
        type: "runtime",
        message: "runtime failed",
        retryable: false,
      },
    });
  });
});
