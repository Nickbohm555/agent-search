import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { loadInternalData, runAgentStream } from "./utils/api";
import { RuntimeAgentRunResponse } from "./utils/api";
import { SAMPLE_INTERNAL_DOCUMENTS } from "./lib/constants";

vi.mock("./utils/api", () => ({
  loadInternalData: vi.fn(),
  runAgentStream: vi.fn(),
}));

const mockedLoadInternalData = vi.mocked(loadInternalData);
const mockedRunAgentStream = vi.mocked(runAgentStream);

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolver) => {
    resolve = resolver;
  });
  return { promise, resolve };
}

function successRunResponse(overrides?: Partial<RuntimeAgentRunResponse>): RuntimeAgentRunResponse {
  return {
    agent_name: "langgraph-scaffold",
    output: "This is the synthesized answer.",
    sub_queries: ["subquery-a", "subquery-b"],
    tool_assignments: [
      { sub_query: "subquery-a", tool: "internal" },
      { sub_query: "subquery-b", tool: "web" },
    ],
    retrieval_results: [],
    validation_results: [
      {
        sub_query: "subquery-a",
        tool: "internal",
        sufficient: true,
        status: "validated",
        attempts: 1,
        follow_up_actions: [],
        attempt_trace: [
          {
            attempt: 1,
            sufficient: true,
            internal_result_count: 2,
            opened_page_count: 0,
            follow_up_action: null,
          },
        ],
        stop_reason: "sufficient",
      },
    ],
    subquery_execution_results: [],
    web_tool_runs: [],
    graph_state: {
      current_step: "synthesis",
      timeline: [
        { step: "decomposition", status: "completed", details: {} },
        { step: "synthesis", status: "completed", details: {} },
      ],
      graph: {},
    },
    ...overrides,
  };
}

describe("App", () => {
  beforeEach(() => {
    vi.resetAllMocks();
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

  it("separates controls, progress, and result into distinct deck panels", () => {
    render(<App />);

    const controlsPanel = screen.getByTestId("controls-panel");
    const progressPanel = screen.getByTestId("progress-panel");
    const resultPanel = screen.getByTestId("result-panel");

    expect(controlsPanel).toHaveTextContent("Control Deck");
    expect(progressPanel).toHaveTextContent("System Progress");
    expect(resultPanel).toHaveTextContent("Final Readout");
    expect(controlsPanel).toHaveClass("deck-panel");
    expect(progressPanel).toHaveClass("deck-panel");
    expect(resultPanel).toHaveClass("deck-panel");
  });

  it("uses consistent chrome markers across section headers", () => {
    render(<App />);

    expect(screen.getByText("ACTION")).toHaveClass("panel-kicker");
    expect(screen.getByText("READOUT")).toHaveClass("panel-kicker");
    expect(screen.getByText("ANSWER")).toHaveClass("panel-kicker");
    expect(document.querySelectorAll(".panel-titlebar")).toHaveLength(3);
  });

  it("keeps action panel before readout panels in DOM order for clear hierarchy", () => {
    render(<App />);

    const controlsPanel = screen.getByTestId("controls-panel");
    const progressPanel = screen.getByTestId("progress-panel");
    const resultPanel = screen.getByTestId("result-panel");

    const panels = Array.from(document.querySelectorAll("[data-testid$='-panel']"));
    expect(panels.indexOf(controlsPanel)).toBe(0);
    expect(panels.indexOf(progressPanel)).toBeGreaterThan(0);
    expect(panels.indexOf(resultPanel)).toBeGreaterThan(panels.indexOf(progressPanel));
  });

  it("retains all deck sections on narrow viewport widths", () => {
    const originalInnerWidth = window.innerWidth;
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 640 });
    try {
      render(<App />);

      expect(screen.getByTestId("controls-panel")).toBeInTheDocument();
      expect(screen.getByTestId("progress-panel")).toBeInTheDocument();
      expect(screen.getByTestId("result-panel")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Load Data" })).toBeInTheDocument();
      expect(screen.getByTestId("final-answer-region")).toBeInTheDocument();
    } finally {
      Object.defineProperty(window, "innerWidth", { configurable: true, value: originalInnerWidth });
    }
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
    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));

    await waitFor(() => {
      expect(mockedLoadInternalData).toHaveBeenCalledWith({
        source_type: "inline",
        documents: SAMPLE_INTERNAL_DOCUMENTS,
      });
    });
    await waitFor(() => {
      expect(screen.getByText("Loaded 2 documents and created 8 chunks.")).toBeInTheDocument();
    });
  });

  it("sends google docs load payload when Google Docs source is selected", async () => {
    mockedLoadInternalData.mockResolvedValue({
      ok: true,
      data: {
        status: "success",
        source_type: "google_docs",
        documents_loaded: 2,
        chunks_created: 6,
      },
    });

    render(<App />);
    fireEvent.click(screen.getByLabelText("Google Docs IDs"));
    fireEvent.change(screen.getByLabelText("Google Doc IDs"), {
      target: { value: "docA, docB" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));

    await waitFor(() => {
      expect(mockedLoadInternalData).toHaveBeenCalledWith({
        source_type: "google_docs",
        document_ids: ["docA", "docB"],
      });
    });
    await waitFor(() => {
      expect(screen.getByText("Loaded 2 documents and created 6 chunks.")).toBeInTheDocument();
    });
  });

  it("shows validation message when Google Docs source is selected without IDs", async () => {
    render(<App />);
    fireEvent.click(screen.getByLabelText("Google Docs IDs"));
    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));

    expect(mockedLoadInternalData).not.toHaveBeenCalled();
    expect(screen.getByText("Enter at least one Google Doc ID.")).toBeInTheDocument();
  });

  it("shows failed load outcome", async () => {
    mockedLoadInternalData.mockResolvedValue({
      ok: false,
      error: {
        type: "network",
        message: "Network error. Please check connection and retry.",
        retryable: true,
      },
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));

    await waitFor(() => {
      expect(screen.getByText("Network error. Please check connection and retry.")).toBeInTheDocument();
    });
  });

  it("shows timeline progress and final answer for successful run", async () => {
    mockedRunAgentStream.mockResolvedValue({
      ok: true,
      data: successRunResponse(),
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "What is the project status?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByText("This is the synthesized answer.")).toBeInTheDocument();
      expect(screen.getByText("Run complete. 2 sub-queries processed.")).toBeInTheDocument();
      expect(screen.getByTestId("timeline-list")).toBeInTheDocument();
      expect(screen.getByText("decomposition")).toBeInTheDocument();
      expect(screen.getByText("subquery-a (internal)")).toBeInTheDocument();
      expect(screen.getByText("subquery-a: validated after 1 attempt")).toBeInTheDocument();
    });
    const timelineItems = screen.getAllByRole("listitem").filter((item) =>
      item.classList.contains("timeline-item"),
    );
    expect(timelineItems[timelineItems.length - 1]).toHaveAttribute("data-current-step", "true");
    expect(timelineItems[0]).toHaveAttribute("data-current-step", "false");
    expect(screen.getByTestId("query-readout")).toHaveTextContent("What is the project status?");
  });

  it("renders timeline detail payloads in progress history readout", async () => {
    mockedRunAgentStream.mockResolvedValue({
      ok: true,
      data: successRunResponse({
        graph_state: {
          current_step: "synthesis",
          timeline: [
            {
              step: "decomposition",
              status: "completed",
              details: {
                query: "timeline details query",
                sub_query_count: 2,
                labels: ["internal", "web"],
              },
            },
          ],
          graph: {},
        },
      }),
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Show timeline details" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByText("labels=internal, web | query=timeline details query | sub_query_count=2")).toBeInTheDocument();
    });
  });

  it("shows retrieval summaries for internal and web sub-queries", async () => {
    mockedRunAgentStream.mockResolvedValue({
      ok: true,
      data: successRunResponse({
        retrieval_results: [
          {
            sub_query: "subquery-a",
            tool: "internal",
            internal_results: [
              {
                chunk_id: 1,
                document_id: 10,
                document_title: "Roadmap",
                source_type: "inline",
                source_ref: "doc://roadmap",
                content: "Roadmap details",
                score: 0.92,
              },
            ],
            web_search_results: [],
            opened_urls: [],
            opened_pages: [],
          },
          {
            sub_query: "subquery-b",
            tool: "web",
            internal_results: [],
            web_search_results: [
              {
                title: "Release notes",
                url: "https://example.com/release",
                snippet: "Latest release details",
              },
            ],
            opened_urls: ["https://example.com/release", "https://example.com/analysis"],
            opened_pages: [
              {
                url: "https://example.com/release",
                title: "Release notes",
                content: "Release body",
              },
              {
                url: "https://example.com/analysis",
                title: "Analysis",
                content: "Analysis body",
              },
            ],
          },
        ],
      }),
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Show retrieval summaries" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByTestId("retrieval-list")).toBeInTheDocument();
      expect(screen.getByText("subquery-a: internal results 1")).toBeInTheDocument();
      expect(screen.getByText("subquery-b: opened 2 web pages")).toBeInTheDocument();
      expect(screen.getByText("https://example.com/release")).toBeInTheDocument();
      expect(screen.getByText("https://example.com/analysis")).toBeInTheDocument();
    });
  });

  it("uses consistent readout styling for load and run status outcomes", async () => {
    mockedLoadInternalData.mockResolvedValue({
      ok: true,
      data: {
        status: "success",
        source_type: "inline",
        documents_loaded: 2,
        chunks_created: 8,
      },
    });
    mockedRunAgentStream.mockResolvedValue({
      ok: true,
      data: successRunResponse(),
    });

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Readout check" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByText("Loaded 2 documents and created 8 chunks.")).toBeInTheDocument();
      expect(screen.getByText("Run complete. 2 sub-queries processed.")).toBeInTheDocument();
    });

    expect(screen.getByTestId("load-status-region")).toHaveClass("readout-block");
    expect(screen.getByTestId("progress-region")).toHaveClass("readout-block");
    expect(screen.getByText("Load Status")).toBeInTheDocument();
    expect(screen.getByText("Run Status")).toBeInTheDocument();
  });

  it("keeps asked query, system progress, and final answer as distinct readout sections", async () => {
    mockedRunAgentStream.mockResolvedValue({
      ok: true,
      data: successRunResponse({ output: "Distinct readout answer." }),
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Which section is what?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByText("Distinct readout answer.")).toBeInTheDocument();
    });

    expect(screen.getByTestId("query-readout")).toHaveTextContent("Which section is what?");
    expect(screen.getByTestId("progress-history-region")).toBeInTheDocument();
    expect(screen.getByTestId("final-answer-region")).toHaveTextContent("Distinct readout answer.");
    expect(screen.getByTestId("final-answer-region")).toHaveClass("answer-dominant");
  });

  it("falls back to sub-query and validation views when graph_state is missing", async () => {
    mockedRunAgentStream.mockResolvedValue({
      ok: true,
      data: {
        agent_name: "langgraph-scaffold",
        output: "Fallback answer.",
        sub_queries: ["subquery-fallback"],
        tool_assignments: [{ sub_query: "subquery-fallback", tool: "web" }],
        retrieval_results: [],
        validation_results: [
          {
            sub_query: "subquery-fallback",
            tool: "web",
            sufficient: false,
            status: "stopped_insufficient",
            attempts: 2,
            follow_up_actions: ["search_more"],
            attempt_trace: [
              {
                attempt: 1,
                sufficient: false,
                internal_result_count: 0,
                opened_page_count: 1,
                follow_up_action: "search_more",
              },
              {
                attempt: 2,
                sufficient: false,
                internal_result_count: 0,
                opened_page_count: 2,
                follow_up_action: null,
              },
            ],
            stop_reason: "max_attempts",
          },
        ],
        subquery_execution_results: [],
        web_tool_runs: [],
        graph_state: null,
      },
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Fallback case" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByTestId("timeline-empty")).toBeInTheDocument();
      expect(screen.getByText("subquery-fallback (web)")).toBeInTheDocument();
      expect(screen.getByText("subquery-fallback: stopped_insufficient after 2 attempts")).toBeInTheDocument();
      expect(screen.getByText("follow-up: search_more")).toBeInTheDocument();
      expect(screen.getByText("attempt 1: insufficient | internal 0 | opened 1 | next search_more")).toBeInTheDocument();
      expect(screen.getByText("Fallback answer.")).toBeInTheDocument();
    });
  });

  it("shows stable empty states for optional progress arrays", async () => {
    mockedRunAgentStream.mockResolvedValue({
      ok: true,
      data: successRunResponse({
        output: "Empty state answer.",
        sub_queries: [],
        tool_assignments: [],
        retrieval_results: [],
        validation_results: [],
        subquery_execution_results: [],
        graph_state: {
          current_step: "synthesis",
          timeline: [],
          graph: {},
        },
      }),
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Empty arrays case" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByTestId("timeline-empty")).toBeInTheDocument();
      expect(screen.getByTestId("subquery-empty")).toBeInTheDocument();
      expect(screen.getByTestId("retrieval-empty")).toBeInTheDocument();
      expect(screen.getByTestId("validation-empty")).toBeInTheDocument();
      expect(screen.getByText("Empty state answer.")).toBeInTheDocument();
    });
  });

  it("shows run failure and preserves query text for retry", async () => {
    mockedRunAgentStream.mockResolvedValue({
      ok: false,
      error: {
        type: "http",
        message: "Request failed with status 503",
        retryable: true,
        statusCode: 503,
      },
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Why did the run fail?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByText("Request failed with status 503")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Query")).toHaveValue("Why did the run fail?");
  });

  it("disables only load control during in-flight load and re-enables after completion", async () => {
    const deferred = createDeferred<Awaited<ReturnType<typeof loadInternalData>>>();
    mockedLoadInternalData.mockImplementation(() => deferred.promise);

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Query stays runnable" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));

    expect(screen.getByRole("button", { name: "Loading..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Run Agent" })).toBeEnabled();

    deferred.resolve({
      ok: true,
      data: {
        status: "success",
        source_type: "inline",
        documents_loaded: 2,
        chunks_created: 8,
      },
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Load Data" })).toBeEnabled();
      expect(screen.getByText("Loaded 2 documents and created 8 chunks.")).toBeInTheDocument();
    });
  });

  it("disables only run control during in-flight run and re-enables after completion", async () => {
    const deferred = createDeferred<Awaited<ReturnType<typeof runAgentStream>>>();
    mockedRunAgentStream.mockImplementation(() => deferred.promise);

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Run lifecycle" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    expect(screen.getByRole("button", { name: "Running..." })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Load Data" })).toBeEnabled();

    deferred.resolve({
      ok: true,
      data: successRunResponse(),
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Run Agent" })).toBeEnabled();
      expect(screen.getByText("This is the synthesized answer.")).toBeInTheDocument();
    });
  });

  it("marks load and run status regions as busy only while requests are in flight", async () => {
    const loadDeferred = createDeferred<Awaited<ReturnType<typeof loadInternalData>>>();
    mockedLoadInternalData.mockImplementation(() => loadDeferred.promise);

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));
    expect(screen.getByTestId("load-status-region")).toHaveAttribute("aria-busy", "true");
    expect(screen.getByTestId("progress-region")).toHaveAttribute("aria-busy", "false");

    loadDeferred.resolve({
      ok: true,
      data: {
        status: "success",
        source_type: "inline",
        documents_loaded: 2,
        chunks_created: 8,
      },
    });

    await waitFor(() => {
      expect(screen.getByTestId("load-status-region")).toHaveAttribute("aria-busy", "false");
    });

    const runDeferred = createDeferred<Awaited<ReturnType<typeof runAgentStream>>>();
    mockedRunAgentStream.mockImplementation(() => runDeferred.promise);

    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Busy semantics" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));
    expect(screen.getByTestId("progress-region")).toHaveAttribute("aria-busy", "true");
    expect(screen.getByTestId("load-status-region")).toHaveAttribute("aria-busy", "false");

    runDeferred.resolve({
      ok: true,
      data: successRunResponse(),
    });

    await waitFor(() => {
      expect(screen.getByTestId("progress-region")).toHaveAttribute("aria-busy", "false");
    });
  });

  it("moves keyboard focus to updated status readouts when load and run complete", async () => {
    mockedLoadInternalData.mockResolvedValue({
      ok: true,
      data: {
        status: "success",
        source_type: "inline",
        documents_loaded: 2,
        chunks_created: 8,
      },
    });
    mockedRunAgentStream.mockResolvedValue({
      ok: true,
      data: successRunResponse(),
    });

    render(<App />);

    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));
    await waitFor(() => {
      expect(screen.getByText("Loaded 2 documents and created 8 chunks.")).toBeInTheDocument();
      expect(screen.getByTestId("load-status-region")).toHaveFocus();
    });

    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Focus behavior query" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));
    await waitFor(() => {
      expect(screen.getByText("Run complete. 2 sub-queries processed.")).toBeInTheDocument();
      expect(screen.getByTestId("progress-region")).toHaveFocus();
    });
  });

  it("shows an in-progress signal in status readouts only while actions are running", async () => {
    const loadDeferred = createDeferred<Awaited<ReturnType<typeof loadInternalData>>>();
    mockedLoadInternalData.mockImplementation(() => loadDeferred.promise);

    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Load Data" }));

    expect(screen.getByTestId("load-status-region")).toHaveAttribute("data-busy-indicator", "active");
    expect(screen.getByTestId("progress-region")).toHaveAttribute("data-busy-indicator", "idle");

    loadDeferred.resolve({
      ok: true,
      data: {
        status: "success",
        source_type: "inline",
        documents_loaded: 2,
        chunks_created: 8,
      },
    });

    await waitFor(() => {
      expect(screen.getByTestId("load-status-region")).toHaveAttribute("data-busy-indicator", "idle");
    });

    const runDeferred = createDeferred<Awaited<ReturnType<typeof runAgentStream>>>();
    mockedRunAgentStream.mockImplementation(() => runDeferred.promise);

    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Signal test" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    expect(screen.getByTestId("progress-region")).toHaveAttribute("data-busy-indicator", "active");
    expect(screen.getByTestId("load-status-region")).toHaveAttribute("data-busy-indicator", "idle");

    runDeferred.resolve({
      ok: true,
      data: successRunResponse(),
    });

    await waitFor(() => {
      expect(screen.getByTestId("progress-region")).toHaveAttribute("data-busy-indicator", "idle");
    });
  });

  it("prevents duplicate in-flight load requests from rapid repeated clicks", async () => {
    const deferred = createDeferred<Awaited<ReturnType<typeof loadInternalData>>>();
    mockedLoadInternalData.mockImplementation(() => deferred.promise);

    render(<App />);
    const loadButton = screen.getByRole("button", { name: "Load Data" });
    fireEvent.click(loadButton);
    fireEvent.click(loadButton);
    fireEvent.click(loadButton);

    expect(mockedLoadInternalData).toHaveBeenCalledTimes(1);

    deferred.resolve({
      ok: true,
      data: {
        status: "success",
        source_type: "inline",
        documents_loaded: 2,
        chunks_created: 8,
      },
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Load Data" })).toBeEnabled();
    });
  });

  it("prevents duplicate in-flight run requests from rapid repeated submits", async () => {
    const deferred = createDeferred<Awaited<ReturnType<typeof runAgentStream>>>();
    mockedRunAgentStream.mockImplementation(() => deferred.promise);

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "No duplicates" } });
    const runButton = screen.getByRole("button", { name: "Run Agent" });
    fireEvent.click(runButton);
    fireEvent.click(runButton);
    fireEvent.click(runButton);

    expect(mockedRunAgentStream).toHaveBeenCalledTimes(1);

    deferred.resolve({
      ok: true,
      data: successRunResponse(),
    });

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Run Agent" })).toBeEnabled();
    });
  });

  it("allows retry in same session after run failure", async () => {
    mockedRunAgentStream
      .mockResolvedValueOnce({
        ok: false,
        error: {
          type: "http",
          message: "Request failed with status 503",
          retryable: true,
          statusCode: 503,
        },
      })
      .mockResolvedValueOnce({
        ok: true,
        data: successRunResponse({ output: "Retry succeeded." }),
      });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Retry query" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByText("Request failed with status 503")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Run Agent" })).toBeEnabled();
    });

    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByText("Retry succeeded.")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Query")).toHaveValue("Retry query");
    expect(mockedRunAgentStream).toHaveBeenCalledTimes(2);
  });

  it("shows streamed sub-queries before completion", async () => {
    mockedRunAgentStream.mockImplementation(async (_payload, handlers) => {
      const partial = successRunResponse({
        output: "",
        sub_queries: ["streamed-subquery"],
        validation_results: [],
        subquery_execution_results: [],
      });
      handlers?.onEvent?.(
        {
          sequence: 2,
          event: "sub_queries",
          data: { sub_queries: ["streamed-subquery"] },
        },
        partial,
      );
      const final = successRunResponse({
        sub_queries: ["streamed-subquery"],
        tool_assignments: [{ sub_query: "streamed-subquery", tool: "internal" }],
        validation_results: [
          {
            sub_query: "streamed-subquery",
            tool: "internal",
            sufficient: true,
            status: "validated",
            attempts: 1,
            follow_up_actions: [],
            attempt_trace: [
              {
                attempt: 1,
                sufficient: true,
                internal_result_count: 1,
                opened_page_count: 0,
                follow_up_action: null,
              },
            ],
            stop_reason: "sufficient",
          },
        ],
        subquery_execution_results: [],
      });
      return { ok: true, data: final };
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Show me streaming" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByText("Streaming progress. 1 sub-queries received.")).toBeInTheDocument();
      expect(screen.getByText("streamed-subquery (unassigned)")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("Run complete. 1 sub-queries processed.")).toBeInTheDocument();
      expect(screen.getByText("streamed-subquery (internal)")).toBeInTheDocument();
      expect(screen.getByText("This is the synthesized answer.")).toBeInTheDocument();
    });
  });

  it("shows heartbeat step updates before completion", async () => {
    mockedRunAgentStream.mockImplementation(async (_payload, handlers) => {
      handlers?.onEvent?.(
        {
          sequence: 1,
          event: "heartbeat",
          data: { step: "decomposition", status: "started", details: {} },
        },
        successRunResponse({
          output: "",
          sub_queries: [],
          tool_assignments: [],
          validation_results: [],
          subquery_execution_results: [],
          graph_state: {
            current_step: "decomposition",
            timeline: [{ step: "decomposition", status: "started", details: {} }],
            graph: {},
          },
        }),
      );
      return { ok: true, data: successRunResponse({ sub_queries: ["subquery-a"] }) };
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "Heartbeat status query" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByText("Step update: decomposition in progress.")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("Run complete. 1 sub-queries processed.")).toBeInTheDocument();
    });
  });
});
