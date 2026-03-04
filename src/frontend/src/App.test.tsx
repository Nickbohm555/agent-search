import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { listWikiSources, loadInternalData } from "./utils/api";
import { RuntimeAgentStreamResponse, streamAgentRun } from "./utils/stream";

vi.mock("./utils/api", () => ({
  listWikiSources: vi.fn(),
  loadInternalData: vi.fn(),
}));

vi.mock("./utils/stream", () => ({
  streamAgentRun: vi.fn(),
}));

const mockedLoadInternalData = vi.mocked(loadInternalData);
const mockedListWikiSources = vi.mocked(listWikiSources);
const mockedStreamAgentRun = vi.mocked(streamAgentRun);
const originalMatchMedia = window.matchMedia;

function mockMatchMedia(matches: boolean): void {
  window.matchMedia = vi.fn().mockImplementation(() => ({
    matches,
    media: "(prefers-reduced-motion: reduce)",
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
  }));
}

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolver) => {
    resolve = resolver;
  });
  return { promise, resolve };
}

function successStreamResponse(overrides?: Partial<RuntimeAgentStreamResponse>): RuntimeAgentStreamResponse {
  return {
    events: [
      { sequence: 1, event: "heartbeat", data: { status: "started", query: "q" } },
      { sequence: 2, event: "progress", data: { step: "decomposition", status: "running" } },
      { sequence: 3, event: "sub_queries", data: { sub_queries: ["subquery-a", "subquery-b"], count: 2 } },
      {
        sequence: 4,
        event: "tool_assignments",
        data: {
          tool_assignments: [
            { sub_query: "subquery-a", tool: "internal" },
            { sub_query: "subquery-b", tool: "web" },
          ],
          count: 2,
        },
      },
      {
        sequence: 5,
        event: "completed",
        data: {
          agent_name: "langgraph-scaffold",
          output: "This is the synthesized answer.",
          thread_id: "thread-app-test",
          checkpoint_id: null,
          sub_queries: ["subquery-a", "subquery-b"],
          tool_assignments: [
            { sub_query: "subquery-a", tool: "internal" },
            { sub_query: "subquery-b", tool: "web" },
          ],
        },
      },
    ],
    completed: {
      agent_name: "langgraph-scaffold",
      output: "This is the synthesized answer.",
      thread_id: "thread-app-test",
      checkpoint_id: null,
      sub_queries: ["subquery-a", "subquery-b"],
      tool_assignments: [
        { sub_query: "subquery-a", tool: "internal" },
        { sub_query: "subquery-b", tool: "web" },
      ],
    },
    ...overrides,
  };
}

function successStreamResponseWithExecutionEvents(): RuntimeAgentStreamResponse {
  return {
    events: [
      { sequence: 1, event: "heartbeat", data: { status: "started", query: "q" } },
      { sequence: 2, event: "progress", data: { step: "decomposition", status: "running" } },
      { sequence: 3, event: "sub_queries", data: { sub_queries: ["subquery-a", "subquery-b"], count: 2 } },
      {
        sequence: 4,
        event: "tool_assignments",
        data: {
          tool_assignments: [
            { sub_query: "subquery-a", tool: "internal" },
            { sub_query: "subquery-b", tool: "web" },
          ],
          count: 2,
        },
      },
      {
        sequence: 5,
        event: "retrieval_result",
        data: {
          sub_query: "subquery-a",
          tool: "internal",
          internal_results: [
            {
              chunk_id: 1,
              document_id: 10,
              document_title: "Doc A",
              source_type: "wiki",
              source_ref: "wiki://a",
              content: "Internal evidence",
              score: 0.9,
              chunk_metadata: {
                topic: "Strait of Hormuz",
                source: "https://en.wikipedia.org/wiki/Strait_of_Hormuz",
              },
            },
          ],
          web_search_results: [],
          opened_urls: [],
          opened_pages: [],
        },
      },
      {
        sequence: 6,
        event: "validation_result",
        data: {
          sub_query: "subquery-a",
          tool: "internal",
          sufficient: true,
          status: "validated",
          attempts: 1,
          follow_up_actions: [],
          stop_reason: "sufficient",
        },
      },
      {
        sequence: 7,
        event: "retrieval_result",
        data: {
          sub_query: "subquery-b",
          tool: "web",
          internal_results: [],
          web_search_results: [
            {
              title: "web source",
              url: "https://example.com/source",
              snippet: "snippet",
            },
          ],
          opened_urls: ["https://example.com/source"],
          opened_pages: [{ url: "https://example.com/source", title: "web source", content: "details" }],
        },
      },
      {
        sequence: 8,
        event: "validation_result",
        data: {
          sub_query: "subquery-b",
          tool: "web",
          sufficient: true,
          status: "validated",
          attempts: 1,
          follow_up_actions: [],
          stop_reason: "sufficient",
        },
      },
      {
        sequence: 9,
        event: "completed",
        data: {
          agent_name: "langgraph-scaffold",
          output: "This is the synthesized answer.",
          thread_id: "thread-app-test",
          checkpoint_id: null,
          sub_queries: ["subquery-a", "subquery-b"],
          tool_assignments: [
            { sub_query: "subquery-a", tool: "internal" },
            { sub_query: "subquery-b", tool: "web" },
          ],
        },
      },
    ],
    completed: {
      agent_name: "langgraph-scaffold",
      output: "This is the synthesized answer.",
      thread_id: "thread-app-test",
      checkpoint_id: null,
      sub_queries: ["subquery-a", "subquery-b"],
      tool_assignments: [
        { sub_query: "subquery-a", tool: "internal" },
        { sub_query: "subquery-b", tool: "web" },
      ],
    },
  };
}

describe("App", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockMatchMedia(false);
    mockedListWikiSources.mockResolvedValue({
      ok: true,
      data: {
        sources: [
          {
            source_id: "strait_of_hormuz",
            label: "Strait of Hormuz",
            article_query: "Strait of Hormuz",
            already_loaded: false,
          },
          {
            source_id: "nato",
            label: "NATO",
            article_query: "NATO",
            already_loaded: false,
          },
        ],
      },
    });
  });

  afterEach(() => {
    window.matchMedia = originalMatchMedia;
  });

  it("renders load/run controls and status regions", () => {
    render(<App />);

    expect(screen.getByRole("button", { name: "Load Data" })).toBeInTheDocument();
    expect(screen.getByTestId("load-status-region")).toBeInTheDocument();
    expect(screen.getByLabelText("Query")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run Agent" })).toBeInTheDocument();
    expect(screen.getByTestId("progress-region")).toBeInTheDocument();
    expect(screen.getByTestId("final-answer-region")).toBeInTheDocument();
    expect(screen.getByTestId("progress-history-region")).toBeInTheDocument();
  });

  it("applies the cyberpunk baseline theme with dark base, neon accents, and distinct surfaces", () => {
    render(<App />);

    expect(screen.getByRole("main")).toHaveAttribute("data-theme", "cyberpunk");
    expect(screen.getByRole("button", { name: "Load Data" })).toHaveClass("neon-action");
    expect(screen.getByRole("button", { name: "Run Agent" })).toHaveClass("neon-action");
    expect(screen.getByTestId("load-status-region")).toHaveClass("status");
    expect(screen.getByTestId("progress-region")).toHaveClass("status");
    expect(document.querySelectorAll(".card").length).toBeGreaterThanOrEqual(3);
  });

  it("marks app reduced-motion state when system preference requests less motion", () => {
    mockMatchMedia(true);
    render(<App />);

    expect(screen.getByRole("main")).toHaveAttribute("data-reduced-motion", "true");
    expect(screen.getByRole("main")).toHaveClass("reduced-motion");
  });

  it("keeps default motion mode when reduced-motion preference is not requested", () => {
    mockMatchMedia(false);
    render(<App />);

    expect(screen.getByRole("main")).toHaveAttribute("data-reduced-motion", "false");
    expect(screen.getByRole("main")).not.toHaveClass("reduced-motion");
  });

  it("shows successful load outcome with counts", async () => {
    mockedLoadInternalData.mockResolvedValue({
      ok: true,
      data: {
        status: "success",
        source_type: "inline",
        documents_loaded: 2,
        chunks_created: 8,
      },
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Load Source"), { target: { value: "inline" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));

    await waitFor(() => {
      expect(screen.getByText("Loaded 2 documents and created 8 chunks.")).toBeInTheDocument();
    });
  });

  it("sends wiki payload and shows wiki success readout when wiki load is selected", async () => {
    mockedLoadInternalData.mockResolvedValue({
      ok: true,
      data: {
        status: "success",
        source_type: "wiki",
        documents_loaded: 1,
        chunks_created: 5,
      },
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Load Source"), { target: { value: "wiki" } });
    await waitFor(() => {
      expect(screen.getByLabelText("Wiki Source")).toBeInTheDocument();
    });
    fireEvent.change(screen.getByLabelText("Wiki Source"), { target: { value: "strait_of_hormuz" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));

    await waitFor(() => {
      expect(mockedLoadInternalData).toHaveBeenCalledWith({
        source_type: "wiki",
        wiki: { source_id: "strait_of_hormuz" },
      });
      expect(screen.getByText("Wiki load complete. Loaded 1 documents and created 5 chunks.")).toBeInTheDocument();
    });
  });

  it("shows clear load error state for wiki load failures", async () => {
    mockedLoadInternalData.mockResolvedValue({
      ok: false,
      error: {
        type: "http",
        message: "Request failed with status 400",
        retryable: false,
        statusCode: 400,
      },
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Load Source"), { target: { value: "wiki" } });
    await waitFor(() => {
      expect(screen.getByLabelText("Wiki Source")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));

    await waitFor(() => {
      expect(screen.getByTestId("load-status-region")).toHaveTextContent("ERROR");
      expect(screen.getByText("Request failed with status 400")).toBeInTheDocument();
    });
  });

  it("prevents wiki load when selected source is already loaded", async () => {
    mockedListWikiSources.mockResolvedValue({
      ok: true,
      data: {
        sources: [
          {
            source_id: "strait_of_hormuz",
            label: "Strait of Hormuz",
            article_query: "Strait of Hormuz",
            already_loaded: true,
          },
        ],
      },
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Load Source"), { target: { value: "wiki" } });

    await waitFor(() => {
      expect(screen.getByText("Selected wiki source is already loaded. Choose another source.")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Load Data" })).toBeDisabled();
    });
    expect(mockedLoadInternalData).not.toHaveBeenCalled();
  });

  it("shows processing readout indicators while load and run are in flight", async () => {
    const loadDeferred = createDeferred<Awaited<ReturnType<typeof loadInternalData>>>();
    const runDeferred = createDeferred<Awaited<ReturnType<typeof streamAgentRun>>>();
    mockedLoadInternalData.mockImplementation(async () => loadDeferred.promise);
    mockedStreamAgentRun.mockImplementation(async () => runDeferred.promise);

    render(<App />);
    fireEvent.change(screen.getByLabelText("Load Source"), { target: { value: "inline" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));

    await waitFor(() => {
      expect(screen.getByTestId("load-status-region")).toHaveAttribute("data-processing", "true");
      expect(screen.getByTestId("load-status-region")).toHaveTextContent("PROCESSING");
      expect(screen.getByRole("button", { name: "Loading..." })).toBeDisabled();
    });

    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Track active run state" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByTestId("progress-region")).toHaveAttribute("data-processing", "true");
      expect(screen.getByTestId("progress-region")).toHaveTextContent("PROCESSING");
      expect(screen.getByRole("button", { name: "Running..." })).toBeDisabled();
    });

    loadDeferred.resolve({
      ok: true,
      data: {
        status: "success",
        source_type: "inline",
        documents_loaded: 2,
        chunks_created: 8,
      },
    });
    runDeferred.resolve({ ok: true, data: successStreamResponse() });

    await waitFor(() => {
      expect(screen.getByTestId("load-status-region")).toHaveAttribute("data-processing", "false");
      expect(screen.getByTestId("progress-region")).toHaveAttribute("data-processing", "false");
      expect(screen.getByText("This is the synthesized answer.")).toBeInTheDocument();
    });
  });

  it("keeps query context and streams progress/sub-queries before final completion", async () => {
    const deferred = createDeferred<Awaited<ReturnType<typeof streamAgentRun>>>();

    mockedStreamAgentRun.mockImplementation(async (_payload, options) => {
      options?.onEvent?.({ sequence: 1, event: "heartbeat", data: { status: "started", query: "q" } });
      options?.onEvent?.({ sequence: 2, event: "progress", data: { step: "decomposition", status: "running" } });
      options?.onEvent?.({ sequence: 3, event: "sub_queries", data: { sub_queries: ["subquery-a"], count: 1 } });
      return deferred.promise;
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "What is the project status?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByTestId("query-readout")).toHaveTextContent("What is the project status?");
      expect(screen.getByText("Generated 1 sub-queries.")).toBeInTheDocument();
      expect(screen.getByText("decomposition")).toBeInTheDocument();
      expect(screen.getByText("subquery-a (unassigned)")).toBeInTheDocument();
      expect(screen.getByText("No answer yet.")).toBeInTheDocument();
    });

    deferred.resolve({ ok: true, data: successStreamResponse() });

    await waitFor(() => {
      expect(screen.getByText("This is the synthesized answer.")).toBeInTheDocument();
      expect(screen.getByText("Run complete. 2 sub-queries processed.")).toBeInTheDocument();
      expect(screen.getByText("subquery-a (internal)")).toBeInTheDocument();
      expect(screen.getByText("subquery-b (web)")).toBeInTheDocument();
    });
  });

  it("shows streamed tool assignments before completion when event arrives", async () => {
    const deferred = createDeferred<Awaited<ReturnType<typeof streamAgentRun>>>();

    mockedStreamAgentRun.mockImplementation(async (_payload, options) => {
      options?.onEvent?.({ sequence: 1, event: "heartbeat", data: { status: "started", query: "q" } });
      options?.onEvent?.({ sequence: 2, event: "sub_queries", data: { sub_queries: ["subquery-a"], count: 1 } });
      options?.onEvent?.({
        sequence: 3,
        event: "tool_assignments",
        data: { tool_assignments: [{ sub_query: "subquery-a", tool: "internal" }], count: 1 },
      });
      return deferred.promise;
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Show in-flight assignment" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByText("Assigned tools for 1 sub-queries.")).toBeInTheDocument();
      expect(screen.getByText("subquery-a (internal)")).toBeInTheDocument();
      expect(screen.getByText("No answer yet.")).toBeInTheDocument();
    });

    deferred.resolve({ ok: true, data: successStreamResponse() });

    await waitFor(() => {
      expect(screen.getByText("This is the synthesized answer.")).toBeInTheDocument();
    });
  });

  it("shows stream failure and preserves query text for retry", async () => {
    mockedStreamAgentRun.mockResolvedValue({
      ok: false,
      error: {
        type: "network",
        message: "Stream interrupted before completion. Please retry.",
        retryable: true,
      },
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Why did the run fail?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByText("Stream interrupted before completion. Please retry.")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Query")).toHaveValue("Why did the run fail?");
    expect(screen.getByTestId("query-readout")).toHaveTextContent("Why did the run fail?");
  });

  it("disables only run control during in-flight run and re-enables after completion", async () => {
    const deferred = createDeferred<Awaited<ReturnType<typeof streamAgentRun>>>();
    mockedStreamAgentRun.mockImplementation(async () => deferred.promise);

    render(<App />);
    fireEvent.change(screen.getByLabelText("Load Source"), { target: { value: "inline" } });
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Run lifecycle" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    expect(screen.getByRole("button", { name: "Running..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Load Data" })).toBeEnabled();

    deferred.resolve({ ok: true, data: successStreamResponse() });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Run Agent" })).toBeEnabled();
      expect(screen.getByText("This is the synthesized answer.")).toBeInTheDocument();
    });
  });

  it("prevents duplicate in-flight run requests from rapid repeated submits", async () => {
    const deferred = createDeferred<Awaited<ReturnType<typeof streamAgentRun>>>();
    mockedStreamAgentRun.mockImplementation(async () => deferred.promise);

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "No duplicates" } });
    const runButton = screen.getByRole("button", { name: "Run Agent" });
    fireEvent.click(runButton);
    fireEvent.click(runButton);
    fireEvent.click(runButton);

    expect(mockedStreamAgentRun).toHaveBeenCalledTimes(1);

    deferred.resolve({ ok: true, data: successStreamResponse() });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Run Agent" })).toBeEnabled();
    });
  });

  it("supports keyboard form submission for run flow", async () => {
    mockedStreamAgentRun.mockResolvedValue({ ok: true, data: successStreamResponse() });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Keyboard submission" } });

    const form = screen.getByLabelText("Query").closest("form");
    expect(form).not.toBeNull();
    fireEvent.submit(form!);

    await waitFor(() => {
      expect(mockedStreamAgentRun).toHaveBeenCalledTimes(1);
      expect(screen.getByText("This is the synthesized answer.")).toBeInTheDocument();
      expect(screen.getByText("Run complete. 2 sub-queries processed.")).toBeInTheDocument();
    });
  });

  it("renders retrieval and validation readouts from streamed execution events on completion", async () => {
    mockedStreamAgentRun.mockResolvedValue({ ok: true, data: successStreamResponseWithExecutionEvents() });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Show execution readouts" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(
        screen.getByText(
          "subquery-a: internal results 1 (topic: Strait of Hormuz, source: https://en.wikipedia.org/wiki/Strait_of_Hormuz)",
        ),
      ).toBeInTheDocument();
      expect(screen.getByText("subquery-b: opened 1 web pages")).toBeInTheDocument();
      expect(screen.getByText("subquery-a: validated")).toBeInTheDocument();
      expect(screen.getByText("subquery-b: validated")).toBeInTheDocument();
    });
  });

  it("supports keyboard form submission for load flow", async () => {
    mockedLoadInternalData.mockResolvedValue({
      ok: true,
      data: {
        status: "success",
        source_type: "inline",
        documents_loaded: 2,
        chunks_created: 8,
      },
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Load Source"), { target: { value: "inline" } });
    const form = screen.getByLabelText("Load Source").closest("form");
    expect(form).not.toBeNull();
    fireEvent.submit(form!);

    await waitFor(() => {
      expect(mockedLoadInternalData).toHaveBeenCalledTimes(1);
      expect(screen.getByText("Loaded 2 documents and created 8 chunks.")).toBeInTheDocument();
    });
  });
});
