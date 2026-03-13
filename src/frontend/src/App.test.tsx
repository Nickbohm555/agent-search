import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

type LifecycleEventShape = {
  event_type: string;
  event_id: string;
  run_id: string;
  thread_id?: string;
  trace_id?: string;
  stage: string;
  status: string;
  emitted_at?: string;
  error?: string | null;
  decomposition_sub_questions?: string[] | null;
  sub_question_artifacts?: unknown[] | null;
  sub_qa?: unknown[] | null;
  output?: string | null;
  result?: unknown;
  elapsed_ms?: number | null;
};

class FakeEventSource {
  static instances: FakeEventSource[] = [];

  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: (() => void) | null = null;
  private readonly listeners = new Map<string, Set<(event: MessageEvent<string>) => void>>();
  closed = false;

  constructor(public readonly url: string) {
    FakeEventSource.instances.push(this);
  }

  close(): void {
    this.closed = true;
  }

  addEventListener(type: string, listener: (event: MessageEvent<string>) => void): void {
    const listenersForType = this.listeners.get(type) ?? new Set<(event: MessageEvent<string>) => void>();
    listenersForType.add(listener);
    this.listeners.set(type, listenersForType);
  }

  removeEventListener(type: string, listener: (event: MessageEvent<string>) => void): void {
    const listenersForType = this.listeners.get(type);
    if (!listenersForType) return;
    listenersForType.delete(listener);
    if (listenersForType.size === 0) {
      this.listeners.delete(type);
    }
  }

  emit(event: LifecycleEventShape): void {
    if (this.closed) return;
    const payload = new MessageEvent<string>(event.event_type, {
      data: JSON.stringify({
        thread_id: "thread-1",
        trace_id: "trace-1",
        emitted_at: "2026-03-13T00:00:00Z",
        error: null,
        ...event,
      }),
    });
    act(() => {
      const listenersForType = this.listeners.get(event.event_type);
      listenersForType?.forEach((listener) => listener(payload));
      if (event.event_type === "message") {
        this.onmessage?.(payload);
      }
    });
  }
}

async function findLatestEventSource(): Promise<FakeEventSource> {
  await waitFor(() => {
    expect(FakeEventSource.instances.length).toBeGreaterThan(0);
  });
  return FakeEventSource.instances[FakeEventSource.instances.length - 1] as FakeEventSource;
}

describe("App wiki source dropdown", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
  });

  it("shows the hardcoded wiki topic list even if wiki source API fails", async () => {
    const fetchMock = vi.fn().mockRejectedValueOnce(new Error("network down"));
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("option", { name: "All Sources" })).toBeInTheDocument();
    expect(await screen.findByRole("option", { name: "Geopolitics" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Strait of Hormuz" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "NATO" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "International Relations" })).toBeInTheDocument();
  });

  it("merges API loaded state into hardcoded wiki topic options", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          sources: [
            {
              source_id: "geopolitics",
              label: "Geopolitics",
              article_query: "Geopolitics",
              already_loaded: true,
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("option", { name: "All Sources" })).toBeInTheDocument();
    expect(await screen.findByRole("option", { name: "Geopolitics (loaded)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "NATO" })).toBeInTheDocument();
  });
});

describe("App run query flow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
  });

  it("shows ordered stage rail and progressive status updates from streamed events", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-1", run_id: "run-1", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-1",
            run_id: "run-1",
            status: "running",
            message: "Stage completed: search",
            stage: "search",
            stages: [],
            decomposition_sub_questions: ["First subquestion?"],
            sub_question_artifacts: [
              {
                sub_question: "First subquestion?",
                expanded_queries: ["First subquestion?"],
                retrieved_docs: [
                  {
                    citation_index: 1,
                    rank: 1,
                    title: "NATO Charter",
                    source: "wikipedia",
                    content: "The North Atlantic Treaty was signed in Washington, D.C. in April 1949.",
                    document_id: "doc-1",
                    score: null,
                  },
                  {
                    citation_index: 2,
                    rank: 2,
                    title: "NATO Timeline",
                    source: "wikipedia",
                    content: "NATO was formed as a collective defense alliance.",
                    document_id: "doc-2",
                    score: null,
                  },
                ],
                retrieval_provenance: [
                  {
                    query: "First subquestion?",
                    query_index: 1,
                    query_rank: 1,
                    document_identity: "doc-1",
                    document_id: "doc-1",
                    source: "wikipedia",
                    deduped: false,
                  },
                  {
                    query: "First subquestion?",
                    query_index: 1,
                    query_rank: 2,
                    document_identity: "doc-1",
                    document_id: "doc-1",
                    source: "wikipedia",
                    deduped: true,
                  },
                  {
                    query: "First subquestion?",
                    query_index: 1,
                    query_rank: 3,
                    document_identity: "doc-2",
                    document_id: "doc-2",
                    source: "wikipedia",
                    deduped: false,
                  },
                ],
              },
            ],
            sub_qa: [],
            output: "",
            result: null,
            error: null,
            cancel_requested: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-1",
            run_id: "run-1",
            status: "success",
            message: "Completed.",
            stage: "synthesize_final",
            stages: [],
            decomposition_sub_questions: ["First subquestion?"],
            sub_question_artifacts: [
              {
                sub_question: "First subquestion?",
                expanded_queries: ["First subquestion?", "First subquestion? alt phrasing"],
                retrieved_docs: [],
                retrieval_provenance: [],
              },
            ],
            sub_qa: [],
            output: "NATO is a military alliance.",
            result: {
              main_question: "What is NATO?",
              sub_qa: [],
              output: "NATO is a military alliance.",
            },
            error: null,
            cancel_requested: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "What is NATO?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    const eventSource = await findLatestEventSource();
    eventSource.emit({
      decomposition_sub_questions: ["First subquestion?"],
      event_type: "stage.completed",
      event_id: "run-1:000002",
      elapsed_ms: 1200,
      run_id: "run-1",
      stage: "search",
      status: "completed",
      sub_qa: [],
      sub_question_artifacts: [
        {
          sub_question: "First subquestion?",
          expanded_queries: ["First subquestion?"],
          retrieved_docs: [
            {
              citation_index: 1,
              rank: 1,
              title: "NATO Charter",
              source: "wikipedia",
              content: "The North Atlantic Treaty was signed in Washington, D.C. in April 1949.",
              document_id: "doc-1",
              score: null,
            },
            {
              citation_index: 2,
              rank: 2,
              title: "NATO Timeline",
              source: "wikipedia",
              content: "NATO was formed as a collective defense alliance.",
              document_id: "doc-2",
              score: null,
            },
          ],
          retrieval_provenance: [
            {
              query: "First subquestion?",
              query_index: 1,
              query_rank: 1,
              document_identity: "doc-1",
              document_id: "doc-1",
              source: "wikipedia",
              deduped: false,
            },
            {
              query: "First subquestion?",
              query_index: 1,
              query_rank: 2,
              document_identity: "doc-1",
              document_id: "doc-1",
              source: "wikipedia",
              deduped: true,
            },
            {
              query: "First subquestion?",
              query_index: 1,
              query_rank: 3,
              document_identity: "doc-2",
              document_id: "doc-2",
              source: "wikipedia",
              deduped: false,
            },
          ],
          reranked_docs: [],
        },
      ],
    });

    expect(screen.getByRole("button", { name: "Running..." })).toBeDisabled();
    expect(await screen.findByText("Run status: stage.completed · search · completed")).toBeInTheDocument();
    expect(getStageStatusText("decompose")).toContain("completed");
    expect(getStageStatusText("search")).toContain("completed");
    expect(getStageStatusText("rerank")).toContain("pending");
    expect(screen.getByRole("heading", { name: "Decompose" })).toBeInTheDocument();
    const decomposeList = screen.getByRole("list", { name: "Decomposed subquestions" });
    expect(decomposeList).toBeInTheDocument();
    expect(within(decomposeList).getByText("First subquestion?")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Expand" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Expanded query groups" })).toBeInTheDocument();
    expect(screen.getByText("Fallback: original only")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Search" })).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Search candidate groups" })).toBeInTheDocument();
    expect(screen.getByText("Merged candidates: 2")).toBeInTheDocument();
    expect(screen.getByText("Raw hits: 3")).toBeInTheDocument();
    expect(screen.getByText("Deduped hits: 2")).toBeInTheDocument();
    expect(screen.getByText("NATO Charter")).toBeInTheDocument();
    expect(screen.getAllByText("wikipedia").length).toBeGreaterThan(0);
    expect(screen.getByText("Subquestion count: 1")).toBeInTheDocument();
    expect(screen.getByText("Ends with ?: yes")).toBeInTheDocument();
    expect(screen.getByText("Dedupe: pass")).toBeInTheDocument();
    expect(screen.getByText("No synthesized answer yet.")).toBeInTheDocument();
    const streamedEventsList = screen.getByRole("list", { name: "Streamed lifecycle events" });
    expect(
      within(streamedEventsList).getAllByText((_, element) => element?.textContent === "stage.completed · search · completed")
        .length,
    ).toBeGreaterThan(0);

    eventSource.emit({
      event_type: "run.completed",
      event_id: "run-1:000003",
      elapsed_ms: 2400,
      output: "NATO is a military alliance.",
      result: {
        final_citations: [],
        main_question: "What is NATO?",
        output: "NATO is a military alliance.",
        sub_qa: [],
      },
      run_id: "run-1",
      stage: "synthesize_final",
      status: "success",
      sub_qa: [],
      sub_question_artifacts: [
        {
          sub_question: "First subquestion?",
          expanded_queries: ["First subquestion?", "First subquestion? alt phrasing"],
          retrieved_docs: [],
          retrieval_provenance: [],
          reranked_docs: [],
        },
      ],
    });

    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });
    expect(getStageStatusText("decompose")).toContain("completed");
    expect(getStageStatusText("final")).toContain("completed");
    expect(screen.getByText("NATO is a military alliance.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Main question" })).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "http://localhost:8000/api/agents/run-async",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: "What is NATO?" }),
        }),
      );
    });

    const stageLabels = screen.getAllByText(/decompose|expand|search|rerank|answer|final/, {
      selector: ".stage-name",
    });
    expect(stageLabels.map((item) => item.textContent)).toEqual([
      "decompose",
      "expand",
      "search",
      "rerank",
      "answer",
      "final",
    ]);
  });

  it("completes from SSE events without polling run-status", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-sse", run_id: "run-sse", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "What is NATO?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    const eventSource = await findLatestEventSource();
    eventSource.emit({
      event_type: "run.completed",
      event_id: "run-sse:000001",
      elapsed_ms: 250,
      output: "NATO is a military alliance.",
      result: {
        final_citations: [],
        main_question: "What is NATO?",
        output: "NATO is a military alliance.",
        sub_qa: [],
      },
      run_id: "run-sse",
      stage: "synthesize_final",
      status: "success",
      sub_qa: [],
      sub_question_artifacts: [],
    });

    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/agents/run-status/"))).toBe(false);
  });

  it("keeps the terminal success state when the SSE stream closes after completion", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-close", run_id: "run-close", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "What is NATO?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    const eventSource = await findLatestEventSource();
    eventSource.emit({
      event_type: "run.completed",
      event_id: "run-close:000001",
      elapsed_ms: 250,
      output: "NATO is a military alliance.",
      result: {
        final_citations: [],
        main_question: "What is NATO?",
        output: "NATO is a military alliance.",
        sub_qa: [],
      },
      run_id: "run-close",
      stage: "synthesize_final",
      status: "success",
      sub_qa: [],
      sub_question_artifacts: [],
    });

    act(() => {
      eventSource.onerror?.();
    });

    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });
    expect(screen.queryByText("Run status: Run event stream disconnected.")).not.toBeInTheDocument();
  });

  it("renders reranked evidence order and fallback indicator", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-rerank", run_id: "run-rerank", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-rerank",
            run_id: "run-rerank",
            status: "running",
            message: "Stage completed: rerank",
            stage: "rerank",
            stages: [],
            decomposition_sub_questions: ["Primary subquestion?", "Fallback subquestion?"],
            sub_question_artifacts: [
              {
                sub_question: "Primary subquestion?",
                expanded_queries: ["Primary subquestion?"],
                retrieved_docs: [
                  {
                    citation_index: 1,
                    rank: 1,
                    title: "Doc A",
                    source: "wiki://a",
                    content: "Doc A body",
                    document_id: "doc-a",
                    score: null,
                  },
                  {
                    citation_index: 2,
                    rank: 2,
                    title: "Doc B",
                    source: "wiki://b",
                    content: "Doc B body",
                    document_id: "doc-b",
                    score: null,
                  },
                ],
                retrieval_provenance: [],
                reranked_docs: [
                  {
                    citation_index: 1,
                    rank: 1,
                    title: "Doc B",
                    source: "wiki://b",
                    content: "Doc B body",
                    document_id: "doc-b",
                    score: 0.98,
                  },
                  {
                    citation_index: 2,
                    rank: 2,
                    title: "Doc A",
                    source: "wiki://a",
                    content: "Doc A body",
                    document_id: "doc-a",
                    score: 0.65,
                  },
                ],
              },
              {
                sub_question: "Fallback subquestion?",
                expanded_queries: ["Fallback subquestion?"],
                retrieved_docs: [
                  {
                    citation_index: 1,
                    rank: 1,
                    title: "Doc C",
                    source: "wiki://c",
                    content: "Doc C body",
                    document_id: "doc-c",
                    score: null,
                  },
                ],
                retrieval_provenance: [],
                reranked_docs: [
                  {
                    citation_index: 1,
                    rank: 1,
                    title: "Doc C",
                    source: "wiki://c",
                    content: "Doc C body",
                    document_id: "doc-c",
                    score: null,
                  },
                ],
              },
            ],
            sub_qa: [
              {
                sub_question: "Primary subquestion?",
                sub_answer: "",
                tool_call_input:
                  '{"rerank_top_n":2,"rerank_provenance":[{"reranked_rank":1,"citation_index":1,"score":0.98,"document_id":"doc-b","source":"wiki://b"},{"reranked_rank":2,"citation_index":2,"score":0.65,"document_id":"doc-a","source":"wiki://a"}]}',
              },
              {
                sub_question: "Fallback subquestion?",
                sub_answer: "",
                tool_call_input:
                  '{"rerank_top_n":1,"rerank_provenance":[{"reranked_rank":1,"citation_index":1,"score":null,"document_id":"doc-c","source":"wiki://c"}]}',
              },
            ],
            output: "",
            result: null,
            error: null,
            cancel_requested: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-rerank",
            run_id: "run-rerank",
            status: "success",
            message: "Completed.",
            stage: "synthesize_final",
            stages: [],
            decomposition_sub_questions: ["Primary subquestion?", "Fallback subquestion?"],
            sub_question_artifacts: [],
            sub_qa: [],
            output: "Rerank run done.",
            result: {
              main_question: "Test rerank view",
              sub_qa: [],
              output: "Rerank run done.",
            },
            error: null,
            cancel_requested: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "Test rerank view" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    const eventSource = await findLatestEventSource();
    eventSource.emit({
      event_type: "stage.completed",
      event_id: "run-rerank:000002",
      elapsed_ms: 1300,
      run_id: "run-rerank",
      stage: "rerank",
      status: "completed",
      decomposition_sub_questions: ["Primary subquestion?", "Fallback subquestion?"],
      output: "",
      sub_qa: [
        {
          sub_question: "Primary subquestion?",
          sub_answer: "",
          tool_call_input:
            '{"rerank_top_n":2,"rerank_provenance":[{"reranked_rank":1,"citation_index":1,"score":0.98,"document_id":"doc-b","source":"wiki://b"},{"reranked_rank":2,"citation_index":2,"score":0.65,"document_id":"doc-a","source":"wiki://a"}]}',
        },
        {
          sub_question: "Fallback subquestion?",
          sub_answer: "",
          tool_call_input:
            '{"rerank_top_n":1,"rerank_provenance":[{"reranked_rank":1,"citation_index":1,"score":null,"document_id":"doc-c","source":"wiki://c"}]}',
        },
      ],
      sub_question_artifacts: [
        {
          sub_question: "Primary subquestion?",
          expanded_queries: ["Primary subquestion?"],
          retrieved_docs: [
            {
              citation_index: 1,
              rank: 1,
              title: "Doc A",
              source: "wiki://a",
              content: "Doc A body",
              document_id: "doc-a",
              score: null,
            },
            {
              citation_index: 2,
              rank: 2,
              title: "Doc B",
              source: "wiki://b",
              content: "Doc B body",
              document_id: "doc-b",
              score: null,
            },
          ],
          retrieval_provenance: [],
          reranked_docs: [
            {
              citation_index: 1,
              rank: 1,
              title: "Doc B",
              source: "wiki://b",
              content: "Doc B body",
              document_id: "doc-b",
              score: 0.98,
            },
            {
              citation_index: 2,
              rank: 2,
              title: "Doc A",
              source: "wiki://a",
              content: "Doc A body",
              document_id: "doc-a",
              score: 0.65,
            },
          ],
        },
        {
          sub_question: "Fallback subquestion?",
          expanded_queries: ["Fallback subquestion?"],
          retrieved_docs: [
            {
              citation_index: 1,
              rank: 1,
              title: "Doc C",
              source: "wiki://c",
              content: "Doc C body",
              document_id: "doc-c",
              score: null,
            },
          ],
          retrieval_provenance: [],
          reranked_docs: [
            {
              citation_index: 1,
              rank: 1,
              title: "Doc C",
              source: "wiki://c",
              content: "Doc C body",
              document_id: "doc-c",
              score: null,
            },
          ],
        },
      ],
    });

    expect(await screen.findByText("Run status: stage.completed · rerank · completed")).toBeInTheDocument();
    const rerankHeading = screen.getByRole("heading", { name: "Rerank" });
    expect(rerankHeading).toBeInTheDocument();
    const rerankSection = rerankHeading.closest("section");
    expect(rerankSection).toBeTruthy();
    expect(screen.getByText("Fallback: reranking bypassed")).toBeInTheDocument();
    expect(screen.getByText("[1] Doc B")).toBeInTheDocument();
    expect(screen.getByText("[2] Doc A")).toBeInTheDocument();
    const orderRows = Array.from((rerankSection as HTMLElement).querySelectorAll(".rerank-order-change"));
    expect(orderRows.some((item) => (item.textContent ?? "").includes("yes"))).toBe(true);
    expect(orderRows.some((item) => (item.textContent ?? "").includes("no"))).toBe(true);
    eventSource.emit({
      event_type: "run.completed",
      event_id: "run-rerank:000003",
      elapsed_ms: 2600,
      output: "Rerank run done.",
      result: {
        final_citations: [],
        main_question: "Test rerank view",
        output: "Rerank run done.",
        sub_qa: [],
      },
      run_id: "run-rerank",
      stage: "synthesize_final",
      status: "success",
      sub_qa: [],
      sub_question_artifacts: [],
    });
    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });
  });

  it("renders subanswers with citation markers and explicit fallback badge", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-answer", run_id: "run-answer", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-answer",
            run_id: "run-answer",
            status: "running",
            message: "Stage completed: answer",
            stage: "answer",
            stages: [],
            decomposition_sub_questions: ["Supported subquestion?", "Unsupported subquestion?"],
            sub_question_artifacts: [
              {
                sub_question: "Supported subquestion?",
                expanded_queries: ["Supported subquestion?"],
                retrieved_docs: [],
                retrieval_provenance: [],
                reranked_docs: [
                  {
                    citation_index: 1,
                    rank: 1,
                    title: "Doc Support A",
                    source: "wiki://support-a",
                    content: "Support A body",
                    document_id: "doc-support-a",
                    score: 0.9,
                  },
                  {
                    citation_index: 2,
                    rank: 2,
                    title: "Doc Support B",
                    source: "wiki://support-b",
                    content: "Support B body",
                    document_id: "doc-support-b",
                    score: 0.8,
                  },
                ],
              },
              {
                sub_question: "Unsupported subquestion?",
                expanded_queries: ["Unsupported subquestion?"],
                retrieved_docs: [],
                retrieval_provenance: [],
                reranked_docs: [],
              },
            ],
            sub_qa: [
              {
                sub_question: "Supported subquestion?",
                sub_answer: "Supported answer [1] with more detail [2].",
                tool_call_input: "{}",
              },
              {
                sub_question: "Unsupported subquestion?",
                sub_answer: "nothing relevant found",
                tool_call_input: "{}",
              },
            ],
            output: "",
            result: null,
            error: null,
            cancel_requested: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-answer",
            run_id: "run-answer",
            status: "success",
            message: "Completed.",
            stage: "synthesize_final",
            stages: [],
            decomposition_sub_questions: ["Supported subquestion?", "Unsupported subquestion?"],
            sub_question_artifacts: [],
            sub_qa: [
              {
                sub_question: "Supported subquestion?",
                sub_answer: "Supported answer [1] with more detail [2].",
                sub_answer_citations: [1, 2],
                tool_call_input: "{}",
              },
              {
                sub_question: "Unsupported subquestion?",
                sub_answer: "nothing relevant found",
                sub_answer_is_fallback: true,
                tool_call_input: "{}",
              },
            ],
            output: "Answer run done.",
            result: {
              main_question: "Test subanswer stage",
              sub_qa: [
                {
                  sub_question: "Supported subquestion?",
                  sub_answer: "Supported answer [1] with more detail [2].",
                  sub_answer_citations: [1, 2],
                  tool_call_input: "{}",
                },
                {
                  sub_question: "Unsupported subquestion?",
                  sub_answer: "nothing relevant found",
                  sub_answer_is_fallback: true,
                  tool_call_input: "{}",
                },
              ],
              output: "Answer run done.",
            },
            error: null,
            cancel_requested: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "Test subanswer stage" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    const eventSource = await findLatestEventSource();
    eventSource.emit({
      event_type: "stage.completed",
      event_id: "run-answer:000002",
      elapsed_ms: 1500,
      run_id: "run-answer",
      stage: "answer",
      status: "completed",
      decomposition_sub_questions: ["Supported subquestion?", "Unsupported subquestion?"],
      output: "",
      sub_qa: [
        {
          sub_question: "Supported subquestion?",
          sub_answer: "Supported answer [1] with more detail [2].",
          tool_call_input: "{}",
        },
        {
          sub_question: "Unsupported subquestion?",
          sub_answer: "nothing relevant found",
          tool_call_input: "{}",
        },
      ],
      sub_question_artifacts: [
        {
          sub_question: "Supported subquestion?",
          expanded_queries: ["Supported subquestion?"],
          retrieved_docs: [],
          retrieval_provenance: [],
          reranked_docs: [
            {
              citation_index: 1,
              rank: 1,
              title: "Doc Support A",
              source: "wiki://support-a",
              content: "Support A body",
              document_id: "doc-support-a",
              score: 0.9,
            },
            {
              citation_index: 2,
              rank: 2,
              title: "Doc Support B",
              source: "wiki://support-b",
              content: "Support B body",
              document_id: "doc-support-b",
              score: 0.8,
            },
          ],
        },
        {
          sub_question: "Unsupported subquestion?",
          expanded_queries: ["Unsupported subquestion?"],
          retrieved_docs: [],
          retrieval_provenance: [],
          reranked_docs: [],
        },
      ],
    });

    expect(await screen.findByText("Run status: stage.completed · answer · completed")).toBeInTheDocument();
    const subanswerHeading = screen.getByRole("heading", { name: "Subanswer" });
    expect(subanswerHeading).toBeInTheDocument();
    const subanswerSection = subanswerHeading.closest("section");
    expect(subanswerSection).toBeTruthy();
    expect(within(subanswerSection as HTMLElement).getByText("Supported answer [1] with more detail [2].")).toBeInTheDocument();
    expect(within(subanswerSection as HTMLElement).getByText("Fallback: nothing relevant found")).toBeInTheDocument();

    const citationOneLinks = screen.getAllByRole("link", { name: "[1]" });
    expect(citationOneLinks.some((item) => item.getAttribute("href") === "#rerank-evidence-lane-1-citation-1")).toBe(true);

    const citationTwoLinks = screen.getAllByRole("link", { name: "[2]" });
    expect(citationTwoLinks.some((item) => item.getAttribute("href") === "#rerank-evidence-lane-1-citation-2")).toBe(true);
    eventSource.emit({
      event_type: "run.completed",
      event_id: "run-answer:000003",
      elapsed_ms: 2800,
      output: "Answer run done.",
      result: {
        final_citations: [],
        main_question: "Test subanswer stage",
        output: "Answer run done.",
        sub_qa: [
          {
            sub_question: "Supported subquestion?",
            sub_answer: "Supported answer [1] with more detail [2].",
            sub_answer_citations: [1, 2],
            tool_call_input: "{}",
          },
          {
            sub_question: "Unsupported subquestion?",
            sub_answer: "nothing relevant found",
            sub_answer_is_fallback: true,
            tool_call_input: "{}",
          },
        ],
      },
      run_id: "run-answer",
      stage: "synthesize_final",
      status: "success",
      sub_qa: [
        {
          sub_question: "Supported subquestion?",
          sub_answer: "Supported answer [1] with more detail [2].",
          sub_answer_citations: [1, 2],
          tool_call_input: "{}",
        },
        {
          sub_question: "Unsupported subquestion?",
          sub_answer: "nothing relevant found",
          sub_answer_is_fallback: true,
          tool_call_input: "{}",
        },
      ],
      sub_question_artifacts: [],
    });
    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });
  });

  it("renders main question and expandable subquestion details from async final result", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-2",
            run_id: "run-2",
            status: "running",
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-2",
            run_id: "run-2",
            status: "success",
            message: "Completed.",
            stage: "synthesize_final",
            stages: [],
            decomposition_sub_questions: ["Which treaty created NATO?"],
            sub_question_artifacts: [
              {
                sub_question: "Which treaty created NATO?",
                expanded_queries: ["Which treaty created NATO?", "NATO founding treaty"],
                retrieved_docs: [],
                retrieval_provenance: [],
              },
            ],
            sub_qa: [
              {
                sub_question: "Which treaty created NATO?",
                sub_answer: "The North Atlantic Treaty created NATO.",
                sub_agent_response: "NATO was established by the Washington Treaty in April 1949.",
                tool_call_input: "{\"query\":\"NATO founding treaty\"}",
              },
            ],
            output: "NATO was formed in 1949.",
            result: {
              output: "NATO was formed in 1949.",
              main_question: "When and why was NATO formed?",
              sub_qa: [
                {
                  sub_question: "Which treaty created NATO?",
                  sub_answer: "The North Atlantic Treaty created NATO.",
                  sub_agent_response: "NATO was established by the Washington Treaty in April 1949.",
                  tool_call_input: "{\"query\":\"NATO founding treaty\"}",
                },
              ],
            },
            error: null,
            cancel_requested: false,
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "When and why was NATO formed?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    const eventSource = await findLatestEventSource();
    eventSource.emit({
      event_type: "run.completed",
      event_id: "run-2:000002",
      elapsed_ms: 1900,
      output: "NATO was formed in 1949.",
      result: {
        main_question: "When and why was NATO formed?",
        output: "NATO was formed in 1949.",
        sub_qa: [
          {
            sub_question: "Which treaty created NATO?",
            sub_answer: "The North Atlantic Treaty created NATO.",
            sub_agent_response: "NATO was established by the Washington Treaty in April 1949.",
            tool_call_input: "{\"query\":\"NATO founding treaty\"}",
          },
        ],
      },
      run_id: "run-2",
      stage: "synthesize_final",
      status: "success",
      sub_qa: [
        {
          sub_question: "Which treaty created NATO?",
          sub_answer: "The North Atlantic Treaty created NATO.",
          sub_agent_response: "NATO was established by the Washington Treaty in April 1949.",
          tool_call_input: "{\"query\":\"NATO founding treaty\"}",
        },
      ],
      sub_question_artifacts: [
        {
          sub_question: "Which treaty created NATO?",
          expanded_queries: ["Which treaty created NATO?", "NATO founding treaty"],
          retrieved_docs: [],
          retrieval_provenance: [],
          reranked_docs: [],
        },
      ],
    });

    expect(await screen.findByRole("heading", { name: "Main question" })).toBeInTheDocument();
    expect(screen.getAllByText("When and why was NATO formed?").length).toBeGreaterThan(0);
    expect(screen.getByText("NATO was formed in 1949.")).toBeInTheDocument();
    expect(screen.getByText("Citation coverage: 0/1 subanswers with citations (0 total citations)")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Subquestions & subanswers" })).toBeInTheDocument();

    const subanswersHeading = screen.getByRole("heading", { name: "Subquestions & subanswers" });
    const subanswersSection = subanswersHeading.closest("section");
    expect(subanswersSection).toBeTruthy();
    const firstSubQuestion = within(subanswersSection as HTMLElement).getByText("Which treaty created NATO?");
    fireEvent.click(firstSubQuestion);

    expect(screen.getAllByText(/The North Atlantic Treaty created NATO\./).length).toBeGreaterThan(0);
    expect(screen.getByText('{"query":"NATO founding treaty"}')).toBeInTheDocument();
  });

  it("keeps the previous successful final synthesis visible until a new run reaches final stage", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-first", run_id: "run-first", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-first",
            run_id: "run-first",
            status: "success",
            message: "Completed.",
            stage: "synthesize_final",
            stages: [],
            decomposition_sub_questions: ["First subquestion?"],
            sub_question_artifacts: [],
            sub_qa: [
              {
                sub_question: "First subquestion?",
                sub_answer: "First answer [1].",
                sub_answer_citations: [1],
                tool_call_input: "{}",
              },
            ],
            output: "First final answer.",
            result: {
              main_question: "First question?",
              sub_qa: [
                {
                  sub_question: "First subquestion?",
                  sub_answer: "First answer [1].",
                  sub_answer_citations: [1],
                  tool_call_input: "{}",
                },
              ],
              output: "First final answer.",
            },
            error: null,
            cancel_requested: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-second", run_id: "run-second", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-second",
            run_id: "run-second",
            status: "running",
            message: "Stage completed: answer",
            stage: "answer",
            stages: [],
            decomposition_sub_questions: ["Second subquestion?"],
            sub_question_artifacts: [],
            sub_qa: [
              {
                sub_question: "Second subquestion?",
                sub_answer: "Second draft answer [2].",
                sub_answer_citations: [2],
                tool_call_input: "{}",
              },
            ],
            output: "Second draft output should not be shown.",
            result: null,
            error: null,
            cancel_requested: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-second",
            run_id: "run-second",
            status: "success",
            message: "Completed.",
            stage: "synthesize_final",
            stages: [],
            decomposition_sub_questions: ["Second subquestion?"],
            sub_question_artifacts: [],
            sub_qa: [
              {
                sub_question: "Second subquestion?",
                sub_answer: "Second final answer [2].",
                sub_answer_citations: [2],
                tool_call_input: "{}",
              },
            ],
            output: "Second final answer.",
            result: {
              main_question: "Second question?",
              sub_qa: [
                {
                  sub_question: "Second subquestion?",
                  sub_answer: "Second final answer [2].",
                  sub_answer_citations: [2],
                  tool_call_input: "{}",
                },
              ],
              output: "Second final answer.",
            },
            error: null,
            cancel_requested: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "First question?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    const firstEventSource = await findLatestEventSource();
    firstEventSource.emit({
      event_type: "run.completed",
      event_id: "run-first:000002",
      elapsed_ms: 2100,
      output: "First final answer.",
      result: {
        final_citations: [],
        main_question: "First question?",
        output: "First final answer.",
        sub_qa: [
          {
            sub_question: "First subquestion?",
            sub_answer: "First answer [1].",
            sub_answer_citations: [1],
            tool_call_input: "{}",
          },
        ],
      },
      run_id: "run-first",
      stage: "synthesize_final",
      status: "success",
      sub_qa: [
        {
          sub_question: "First subquestion?",
          sub_answer: "First answer [1].",
          sub_answer_citations: [1],
          tool_call_input: "{}",
        },
      ],
      sub_question_artifacts: [],
    });

    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });
    expect(screen.getByText("First final answer.")).toBeInTheDocument();
    expect(screen.getByText("Citation coverage: 1/1 subanswers with citations (1 total citations)")).toBeInTheDocument();

    fireEvent.change(textarea, { target: { value: "Second question?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));
    const secondEventSource = await findLatestEventSource();
    secondEventSource.emit({
      event_type: "stage.completed",
      event_id: "run-second:000002",
      elapsed_ms: 1200,
      run_id: "run-second",
      stage: "answer",
      status: "completed",
      decomposition_sub_questions: ["Second subquestion?"],
      output: "Second draft output should not be shown.",
      sub_qa: [
        {
          sub_question: "Second subquestion?",
          sub_answer: "Second draft answer [2].",
          sub_answer_citations: [2],
          tool_call_input: "{}",
        },
      ],
      sub_question_artifacts: [],
    });

    expect(await screen.findByText("Run status: stage.completed · answer · completed")).toBeInTheDocument();
    expect(screen.getByText("Showing previous successful synthesis while current run is in progress.")).toBeInTheDocument();
    expect(screen.getByText("First final answer.")).toBeInTheDocument();
    expect(screen.queryByText("Second draft output should not be shown.")).not.toBeInTheDocument();
    secondEventSource.emit({
      event_type: "run.completed",
      event_id: "run-second:000003",
      elapsed_ms: 2600,
      output: "Second final answer.",
      result: {
        final_citations: [],
        main_question: "Second question?",
        output: "Second final answer.",
        sub_qa: [
          {
            sub_question: "Second subquestion?",
            sub_answer: "Second final answer [2].",
            sub_answer_citations: [2],
            tool_call_input: "{}",
          },
        ],
      },
      run_id: "run-second",
      stage: "synthesize_final",
      status: "success",
      sub_qa: [
        {
          sub_question: "Second subquestion?",
          sub_answer: "Second final answer [2].",
          sub_answer_citations: [2],
          tool_call_input: "{}",
        },
      ],
      sub_question_artifacts: [],
    });

    await waitFor(() => {
      expect(screen.getByText("Second final answer.")).toBeInTheDocument();
    });
    expect(screen.queryByText("First final answer.")).not.toBeInTheDocument();
  });

  it("shows an error message when run request fails", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "server error" }), {
          status: 500,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "What happened?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    expect(await screen.findByText(/Request failed with status 500/)).toBeInTheDocument();
  });
});

function getStageStatusText(stageName: string): string {
  const stageLabel = screen.getByText(stageName);
  const stageItem = stageLabel.closest("li");
  expect(stageItem).toBeTruthy();
  return stageItem?.textContent ?? "";
}
