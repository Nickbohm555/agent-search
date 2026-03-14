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
  sub_items?: unknown[] | null;
  output?: string | null;
  result?: unknown;
  elapsed_ms?: number | null;
  interrupt_payload?: unknown;
  checkpoint_id?: string | null;
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

  it("defaults both runtime controls on and lets each toggle change independently", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(
      new Response(JSON.stringify({ sources: [] }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const rerankToggle = await screen.findByLabelText("Rerank results");
    const queryExpansionToggle = screen.getByLabelText("Expand queries");

    expect(rerankToggle).toBeChecked();
    expect(queryExpansionToggle).toBeChecked();

    fireEvent.click(rerankToggle);
    expect(rerankToggle).not.toBeChecked();
    expect(queryExpansionToggle).toBeChecked();

    fireEvent.click(queryExpansionToggle);
    expect(rerankToggle).not.toBeChecked();
    expect(queryExpansionToggle).not.toBeChecked();

    fireEvent.click(rerankToggle);
    expect(rerankToggle).toBeChecked();
    expect(queryExpansionToggle).not.toBeChecked();
  });

  it("serializes rerank and query expansion toggles to runtime_config independently", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-runtime-config", run_id: "run-runtime-config", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "What changed?" } });
    fireEvent.click(screen.getByLabelText("Rerank results"));
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "http://localhost:8000/api/agents/run-async",
        expect.objectContaining({
          body: JSON.stringify({
            query: "What changed?",
            runtime_config: {
              rerank: { enabled: false },
              query_expansion: { enabled: true },
            },
          }),
        }),
      );
    });
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
            sub_items: [],
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
            sub_items: [],
            output: "NATO is a military alliance.",
            result: {
              main_question: "What is NATO?",
              sub_items: [],
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
      sub_items: [],
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
        sub_items: [],
      },
      run_id: "run-1",
      stage: "synthesize_final",
      status: "success",
      sub_items: [],
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
          body: JSON.stringify({
            query: "What is NATO?",
            runtime_config: {
              rerank: { enabled: true },
              query_expansion: { enabled: true },
            },
          }),
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
        sub_items: [],
      },
      run_id: "run-sse",
      stage: "synthesize_final",
      status: "success",
      sub_items: [],
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
        sub_items: [],
      },
      run_id: "run-close",
      stage: "synthesize_final",
      status: "success",
      sub_items: [],
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

  it("treats a completed final snapshot as terminal success when run.completed is absent", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-final-snapshot", run_id: "run-final-snapshot", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "Snapshot-only completion" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    const eventSource = await findLatestEventSource();
    eventSource.emit({
      event_type: "stage.snapshot",
      event_id: "run-final-snapshot:000048",
      elapsed_ms: 950,
      output: "Snapshot-only answer.",
      result: {
        final_citations: [],
        main_question: "Snapshot-only completion",
        output: "Snapshot-only answer.",
        sub_items: [],
      },
      run_id: "run-final-snapshot",
      stage: "synthesize_final",
      status: "completed",
      sub_items: [],
      sub_question_artifacts: [],
    });

    act(() => {
      eventSource.onerror?.();
    });

    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });
    expect(screen.getByText("Snapshot-only answer.")).toBeInTheDocument();
    expect(screen.queryByText("Run status: Run event stream disconnected.")).not.toBeInTheDocument();
  });

  it("shows paused subquestion review and resumes to completion with typed decisions", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-hitl", run_id: "run-hitl", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-hitl",
            run_id: "run-hitl",
            status: "running",
            message: "Resume accepted.",
            stage: "subquestions_ready",
            stages: [],
            decomposition_sub_questions: ["Keep this?", "Change this?", "Remove this?"],
            sub_question_artifacts: [],
            sub_items: [],
            output: "",
            result: null,
            error: null,
            cancel_requested: false,
            checkpoint_id: "checkpoint-42",
            interrupt_payload: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "Review my subquestions" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    const pausedEventSource = await findLatestEventSource();
    pausedEventSource.emit({
      event_type: "run.paused",
      event_id: "run-hitl:000001",
      run_id: "run-hitl",
      stage: "subquestions_ready",
      status: "paused",
      checkpoint_id: "checkpoint-42",
      decomposition_sub_questions: ["Keep this?", "Change this?", "Remove this?"],
      sub_items: [],
      sub_question_artifacts: [],
      interrupt_payload: {
        checkpoint_id: "checkpoint-42",
        kind: "subquestion_review",
        stage: "subquestions_ready",
        subquestions: [
          { subquestion_id: "sq-1", sub_question: "Keep this?" },
          { subquestion_id: "sq-2", sub_question: "Change this?" },
          { subquestion_id: "sq-3", sub_question: "Remove this?" },
        ],
      },
    });

    expect(await screen.findByRole("heading", { name: "Subquestion Review" })).toBeInTheDocument();
    expect(screen.getByText("Run status: Run paused for subquestion review.")).toBeInTheDocument();
    expect(screen.queryByText(/run\.paused · subquestions_ready · paused/)).not.toBeInTheDocument();

    const decisions = screen.getAllByLabelText("Decision");
    fireEvent.change(decisions[1] as HTMLElement, { target: { value: "edit" } });
    fireEvent.change(screen.getByLabelText("Edited text"), { target: { value: "Rewritten subquestion?" } });
    fireEvent.change(decisions[2] as HTMLElement, { target: { value: "deny" } });
    fireEvent.click(screen.getByRole("button", { name: "Resume Run" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        3,
        "http://localhost:8000/api/agents/run-resume/job-hitl",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            resume: {
              checkpoint_id: "checkpoint-42",
              decisions: [
                { subquestion_id: "sq-1", action: "approve" },
                { subquestion_id: "sq-2", action: "edit", edited_text: "Rewritten subquestion?" },
                { subquestion_id: "sq-3", action: "deny" },
              ],
            },
          }),
        }),
      );
    });
    expect(FakeEventSource.instances[1]?.url).toContain("after_event_id=run-hitl%3A000001");

    expect(await screen.findByText("Run status: Resume accepted.")).toBeInTheDocument();

    const resumedEventSource = await findLatestEventSource();
    expect(resumedEventSource).not.toBe(pausedEventSource);
    resumedEventSource.emit({
      event_type: "run.completed",
      event_id: "run-hitl:000002",
      run_id: "run-hitl",
      stage: "synthesize_final",
      status: "success",
      output: "Resumed answer.",
      result: {
        final_citations: [],
        main_question: "Review my subquestions",
        output: "Resumed answer.",
        sub_items: [],
      },
      sub_items: [],
      sub_question_artifacts: [],
    });

    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });
    expect(screen.getByText("Resumed answer.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Subquestion Review" })).not.toBeInTheDocument();
  });

  it("skips paused subquestion review with skip decisions and resumes to completion", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-hitl-skip", run_id: "run-hitl-skip", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-hitl-skip",
            run_id: "run-hitl-skip",
            status: "running",
            message: "Resume accepted.",
            stage: "subquestions_ready",
            stages: [],
            decomposition_sub_questions: ["Keep this?", "Change this?", "Remove this?"],
            sub_question_artifacts: [],
            sub_items: [],
            output: "",
            result: null,
            error: null,
            cancel_requested: false,
            checkpoint_id: "checkpoint-skip",
            interrupt_payload: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "Skip my subquestion review" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    const pausedEventSource = await findLatestEventSource();
    pausedEventSource.emit({
      event_type: "run.paused",
      event_id: "run-hitl-skip:000001",
      run_id: "run-hitl-skip",
      stage: "subquestions_ready",
      status: "paused",
      checkpoint_id: "checkpoint-skip",
      decomposition_sub_questions: ["Keep this?", "Change this?", "Remove this?"],
      sub_items: [],
      sub_question_artifacts: [],
      interrupt_payload: {
        checkpoint_id: "checkpoint-skip",
        kind: "subquestion_review",
        stage: "subquestions_ready",
        subquestions: [
          { subquestion_id: "sq-1", sub_question: "Keep this?" },
          { subquestion_id: "sq-2", sub_question: "Change this?" },
          { subquestion_id: "sq-3", sub_question: "Remove this?" },
        ],
      },
    });

    expect(await screen.findByRole("heading", { name: "Subquestion Review" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Skip Review" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        3,
        "http://localhost:8000/api/agents/run-resume/job-hitl-skip",
        expect.objectContaining({
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            resume: {
              checkpoint_id: "checkpoint-skip",
              decisions: [
                { subquestion_id: "sq-1", action: "skip" },
                { subquestion_id: "sq-2", action: "skip" },
                { subquestion_id: "sq-3", action: "skip" },
              ],
            },
          }),
        }),
      );
    });
    expect(FakeEventSource.instances[1]?.url).toContain("after_event_id=run-hitl-skip%3A000001");

    expect(await screen.findByText("Run status: Resume accepted.")).toBeInTheDocument();
    expect(screen.queryByText(/run\.paused · subquestions_ready · paused/)).not.toBeInTheDocument();

    const resumedEventSource = await findLatestEventSource();
    expect(resumedEventSource).not.toBe(pausedEventSource);
    resumedEventSource.emit({
      event_type: "run.completed",
      event_id: "run-hitl-skip:000002",
      run_id: "run-hitl-skip",
      stage: "synthesize_final",
      status: "success",
      output: "Skipped review answer.",
      result: {
        final_citations: [],
        main_question: "Skip my subquestion review",
        output: "Skipped review answer.",
        sub_items: [],
      },
      sub_items: [],
      sub_question_artifacts: [],
    });

    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });
    expect(screen.getByText("Skipped review answer.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Subquestion Review" })).not.toBeInTheDocument();
  });

  it("ignores replayed paused events after resume when the SSE stream restarts from the beginning", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-hitl-replay", run_id: "run-hitl-replay", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-hitl-replay",
            run_id: "run-hitl-replay",
            status: "running",
            message: "Resume accepted.",
            stage: "subquestions_ready",
            stages: [],
            decomposition_sub_questions: ["Keep this?"],
            sub_question_artifacts: [],
            sub_items: [],
            output: "",
            result: null,
            error: null,
            cancel_requested: false,
            checkpoint_id: "checkpoint-replay",
            interrupt_payload: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "Replay paused events after resume" } });
    fireEvent.click(screen.getByLabelText("Enable subquestion HITL"));
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    const pausedEventSource = await findLatestEventSource();
    pausedEventSource.emit({
      event_type: "run.paused",
      event_id: "run-hitl-replay:000001",
      run_id: "run-hitl-replay",
      stage: "subquestions_ready",
      status: "paused",
      checkpoint_id: "checkpoint-replay",
      decomposition_sub_questions: ["Keep this?"],
      sub_items: [],
      sub_question_artifacts: [],
      interrupt_payload: {
        checkpoint_id: "checkpoint-replay",
        kind: "subquestion_review",
        stage: "subquestions_ready",
        subquestions: [{ subquestion_id: "sq-1", sub_question: "Keep this?" }],
      },
    });

    expect(await screen.findByRole("heading", { name: "Subquestion Review" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Skip Review" }));

    const resumedEventSource = await findLatestEventSource();
    expect(resumedEventSource).not.toBe(pausedEventSource);

    resumedEventSource.emit({
      event_type: "run.paused",
      event_id: "run-hitl-replay:000001",
      run_id: "run-hitl-replay",
      stage: "subquestions_ready",
      status: "paused",
      checkpoint_id: "checkpoint-replay",
      decomposition_sub_questions: ["Keep this?"],
      sub_items: [],
      sub_question_artifacts: [],
      interrupt_payload: {
        checkpoint_id: "checkpoint-replay",
        kind: "subquestion_review",
        stage: "subquestions_ready",
        subquestions: [{ subquestion_id: "sq-1", sub_question: "Keep this?" }],
      },
    });

    resumedEventSource.emit({
      event_type: "run.completed",
      event_id: "run-hitl-replay:000002",
      run_id: "run-hitl-replay",
      stage: "synthesize_final",
      status: "success",
      output: "Replay-safe answer.",
      result: {
        final_citations: [],
        main_question: "Replay paused events after resume",
        output: "Replay-safe answer.",
        sub_items: [],
      },
      sub_items: [],
      sub_question_artifacts: [],
    });

    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });
    expect(screen.getByText("Replay-safe answer.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Subquestion Review" })).not.toBeInTheDocument();
  });

  it("ignores stale paused-stream errors after resume opens a new SSE connection", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-hitl-stale-error", run_id: "run-hitl-stale-error", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            job_id: "job-hitl-stale-error",
            run_id: "run-hitl-stale-error",
            status: "running",
            message: "Resume accepted.",
            stage: "subquestions_ready",
            stages: [],
            decomposition_sub_questions: ["Keep this?"],
            sub_question_artifacts: [],
            sub_items: [],
            output: "",
            result: null,
            error: null,
            cancel_requested: false,
            checkpoint_id: "checkpoint-stale-error",
            interrupt_payload: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "Ignore stale paused stream errors" } });
    fireEvent.click(screen.getByLabelText("Enable subquestion HITL"));
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    const pausedEventSource = await findLatestEventSource();
    pausedEventSource.emit({
      event_type: "run.paused",
      event_id: "run-hitl-stale-error:000001",
      run_id: "run-hitl-stale-error",
      stage: "subquestions_ready",
      status: "paused",
      checkpoint_id: "checkpoint-stale-error",
      decomposition_sub_questions: ["Keep this?"],
      sub_items: [],
      sub_question_artifacts: [],
      interrupt_payload: {
        checkpoint_id: "checkpoint-stale-error",
        kind: "subquestion_review",
        stage: "subquestions_ready",
        subquestions: [{ subquestion_id: "sq-1", sub_question: "Keep this?" }],
      },
    });

    expect(await screen.findByRole("heading", { name: "Subquestion Review" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Skip Review" }));

    const resumedEventSource = await findLatestEventSource();
    expect(resumedEventSource).not.toBe(pausedEventSource);
    expect(pausedEventSource.onerror).toBeNull();

    act(() => {
      pausedEventSource.onerror?.();
    });

    resumedEventSource.emit({
      event_type: "run.completed",
      event_id: "run-hitl-stale-error:000002",
      run_id: "run-hitl-stale-error",
      stage: "synthesize_final",
      status: "success",
      output: "Stale error ignored answer.",
      result: {
        final_citations: [],
        main_question: "Ignore stale paused stream errors",
        output: "Stale error ignored answer.",
        sub_items: [],
      },
      sub_items: [],
      sub_question_artifacts: [],
    });

    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });
    expect(screen.getByText("Stale error ignored answer.")).toBeInTheDocument();
    expect(screen.queryByText("Run status: Run event stream disconnected.")).not.toBeInTheDocument();
  });

  it("keeps non-HITL runs on the default completion path without review UI or resume calls", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-no-hitl", run_id: "run-no-hitl", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "Standard async run" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    const eventSource = await findLatestEventSource();
    eventSource.emit({
      event_type: "run.completed",
      event_id: "run-no-hitl:000001",
      run_id: "run-no-hitl",
      stage: "synthesize_final",
      status: "success",
      output: "Standard async answer.",
      result: {
        final_citations: [],
        main_question: "Standard async run",
        output: "Standard async answer.",
        sub_items: [],
      },
      sub_items: [],
      sub_question_artifacts: [],
    });

    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes("/api/agents/run-resume/"))).toBe(false);
    expect(screen.queryByRole("heading", { name: "Subquestion Review" })).not.toBeInTheDocument();
    expect(screen.queryByText("Run status: Run paused for subquestion review.")).not.toBeInTheDocument();
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
            sub_items: [
              ["Primary subquestion?", ""],
              ["Fallback subquestion?", ""],
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
            sub_items: [],
            output: "Rerank run done.",
            result: {
              main_question: "Test rerank view",
              sub_items: [],
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
      sub_items: [
        ["Primary subquestion?", ""],
        ["Fallback subquestion?", ""],
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
        sub_items: [],
      },
      run_id: "run-rerank",
      stage: "synthesize_final",
      status: "success",
      sub_items: [],
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
            sub_items: [
              ["Supported subquestion?", "Supported answer [1] with more detail [2]."],
              ["Unsupported subquestion?", "nothing relevant found"],
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
            sub_items: [
              ["Supported subquestion?", "Supported answer [1] with more detail [2]."],
              ["Unsupported subquestion?", "nothing relevant found"],
            ],
            output: "Answer run done.",
            result: {
              main_question: "Test subanswer stage",
              sub_items: [
                ["Supported subquestion?", "Supported answer [1] with more detail [2]."],
                ["Unsupported subquestion?", "nothing relevant found"],
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
      sub_items: [
        ["Supported subquestion?", "Supported answer [1] with more detail [2]."],
        ["Unsupported subquestion?", "nothing relevant found"],
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
        sub_items: [
          ["Supported subquestion?", "Supported answer [1] with more detail [2]."],
          ["Unsupported subquestion?", "nothing relevant found"],
        ],
      },
      run_id: "run-answer",
      stage: "synthesize_final",
      status: "success",
      sub_items: [
        ["Supported subquestion?", "Supported answer [1] with more detail [2]."],
        ["Unsupported subquestion?", "nothing relevant found"],
      ],
      sub_question_artifacts: [],
    });
    await waitFor(() => {
      expect(screen.getByText("Run status: run.completed · synthesize_final · success")).toBeInTheDocument();
    });
  });

  it("renders subanswers from sub_items payloads during streamed and final updates", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-sub-answers", run_id: "run-sub-answers", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "What changed in the contract?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    const eventSource = await findLatestEventSource();
    eventSource.emit({
      event_type: "stage.completed",
      event_id: "run-sub-answers:000002",
      elapsed_ms: 1400,
      run_id: "run-sub-answers",
      stage: "answer",
      status: "completed",
      decomposition_sub_questions: ["What changed in the contract?"],
      sub_items: [["What changed in the contract?", "The payload now includes sub_items [1]."]],
      sub_question_artifacts: [
        {
          sub_question: "What changed in the contract?",
          expanded_queries: ["What changed in the contract?"],
          retrieved_docs: [],
          retrieval_provenance: [],
          reranked_docs: [
            {
              citation_index: 1,
              rank: 1,
              title: "Contract note",
              source: "wiki://contract-note",
              content: "The response now exposes sub_items.",
              document_id: "doc-contract-note",
              score: 0.8,
            },
          ],
        },
      ],
      output: "",
    });

    expect(await screen.findByText("Run status: stage.completed · answer · completed")).toBeInTheDocument();
    const subanswerHeading = screen.getByRole("heading", { name: "Subanswer" });
    const subanswerSection = subanswerHeading.closest("section");
    expect(subanswerSection).toBeTruthy();
    expect(within(subanswerSection as HTMLElement).getByText("The payload now includes sub_items [1].")).toBeInTheDocument();

    eventSource.emit({
      event_type: "run.completed",
      event_id: "run-sub-answers:000003",
      elapsed_ms: 2500,
      run_id: "run-sub-answers",
      stage: "synthesize_final",
      status: "success",
      output: "The contract now exposes sub_items without extra aliases.",
      result: {
        final_citations: [],
        main_question: "What changed in the contract?",
        output: "The contract now exposes sub_items without extra aliases.",
        sub_items: [["What changed in the contract?", "The payload now includes sub_items [1]."]],
      },
      sub_question_artifacts: [],
    });

    await waitFor(() => {
      expect(screen.getByText("The contract now exposes sub_items without extra aliases.")).toBeInTheDocument();
    });
    expect(screen.getByText("Citation coverage: 1/1 subanswers with citations (1 total citations)")).toBeInTheDocument();
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
            sub_items: [["Which treaty created NATO?", "The North Atlantic Treaty created NATO."]],
            output: "NATO was formed in 1949.",
            result: {
              output: "NATO was formed in 1949.",
              main_question: "When and why was NATO formed?",
              sub_items: [["Which treaty created NATO?", "The North Atlantic Treaty created NATO."]],
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
        sub_items: [["Which treaty created NATO?", "The North Atlantic Treaty created NATO."]],
      },
      run_id: "run-2",
      stage: "synthesize_final",
      status: "success",
      sub_items: [["Which treaty created NATO?", "The North Atlantic Treaty created NATO."]],
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
            sub_items: [["First subquestion?", "First answer [1]."]],
            output: "First final answer.",
            result: {
              main_question: "First question?",
              sub_items: [["First subquestion?", "First answer [1]."]],
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
            sub_items: [["Second subquestion?", "Second draft answer [2]."]],
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
            sub_items: [["Second subquestion?", "Second final answer [2]."]],
            output: "Second final answer.",
            result: {
              main_question: "Second question?",
              sub_items: [["Second subquestion?", "Second final answer [2]."]],
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
        sub_items: [["First subquestion?", "First answer [1]."]],
      },
      run_id: "run-first",
      stage: "synthesize_final",
      status: "success",
      sub_items: [["First subquestion?", "First answer [1]."]],
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
      sub_items: [["Second subquestion?", "Second draft answer [2]."]],
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
        sub_items: [["Second subquestion?", "Second final answer [2]."]],
      },
      run_id: "run-second",
      stage: "synthesize_final",
      status: "success",
      sub_items: [["Second subquestion?", "Second final answer [2]."]],
      sub_question_artifacts: [],
    });

    await waitFor(() => {
      expect(screen.getByText("Second final answer.")).toBeInTheDocument();
    });
    expect(screen.queryByText("First final answer.")).not.toBeInTheDocument();
  });

  it("keeps the previous additive final synthesis visible while rendering streamed subanswers for the next run", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-additive-first", run_id: "run-additive-first", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-additive-second", run_id: "run-additive-second", status: "running" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    const textarea = await screen.findByPlaceholderText("Ask a question from loaded wiki content");
    fireEvent.change(textarea, { target: { value: "First additive question?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    const firstEventSource = await findLatestEventSource();
    firstEventSource.emit({
      event_type: "run.completed",
      event_id: "run-additive-first:000002",
      elapsed_ms: 2100,
      output: "First additive final answer.",
      result: {
        final_citations: [],
        main_question: "First additive question?",
        output: "First additive final answer.",
        sub_items: [["First additive subquestion?", "First additive answer [1]."]],
      },
      run_id: "run-additive-first",
      stage: "synthesize_final",
      status: "success",
      sub_items: [["First additive subquestion?", "First additive answer [1]."]],
      sub_question_artifacts: [],
    });

    await waitFor(() => {
      expect(screen.getByText("First additive final answer.")).toBeInTheDocument();
    });
    expect(screen.getByText("First additive answer [1].")).toBeInTheDocument();
    expect(screen.getByText("Citation coverage: 1/1 subanswers with citations (1 total citations)")).toBeInTheDocument();

    fireEvent.change(textarea, { target: { value: "Second additive question?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    const secondEventSource = await findLatestEventSource();
    secondEventSource.emit({
      event_type: "stage.completed",
      event_id: "run-additive-second:000002",
      elapsed_ms: 1300,
      run_id: "run-additive-second",
      stage: "answer",
      status: "completed",
      decomposition_sub_questions: ["Second additive subquestion?"],
      output: "Second additive draft output.",
      sub_items: [["Second additive subquestion?", "Second additive draft answer [2]."]],
      sub_question_artifacts: [],
    });

    expect(await screen.findByText("Run status: stage.completed · answer · completed")).toBeInTheDocument();
    expect(screen.getByText("Showing previous successful synthesis while current run is in progress.")).toBeInTheDocument();
    expect(screen.getByText("First additive final answer.")).toBeInTheDocument();
    expect(screen.queryByText("Second additive draft output.")).not.toBeInTheDocument();
    expect(screen.getByText("Second additive draft answer [2].")).toBeInTheDocument();
    expect(screen.getByText("Citation coverage: 1/1 subanswers with citations (1 total citations)")).toBeInTheDocument();
  });

  it("derives final citations from final-stage snapshot artifacts when terminal result omits them", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ sources: [] }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ job_id: "job-final-citations", run_id: "run-final-citations", status: "running" }), {
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
      event_type: "stage.snapshot",
      event_id: "run-final-citations:000002",
      run_id: "run-final-citations",
      stage: "synthesize_final",
      status: "completed",
      output: "NATO is an alliance [1].",
      sub_items: [["What is NATO?", "NATO is an alliance [1]."]],
      sub_question_artifacts: [
        {
          sub_question: "What is NATO?",
          expanded_queries: ["What is NATO?"],
          retrieved_docs: [],
          retrieval_provenance: [],
          reranked_docs: [],
          citation_rows_by_index: {
            1: {
              citation_index: 1,
              rank: 1,
              title: "NATO",
              source: "https://en.wikipedia.org/wiki/NATO",
              content: "NATO reference content.",
              document_id: "doc-nato",
              score: 0.9,
            },
          },
        },
      ],
    });

    await waitFor(() => {
      expect(screen.getByText("Citation coverage: 1/1 subanswers with citations (1 total citations)")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: "[1] https://en.wikipedia.org/wiki/NATO" })).toBeInTheDocument();
    expect(screen.queryByText("NATO reference content.")).not.toBeInTheDocument();
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
