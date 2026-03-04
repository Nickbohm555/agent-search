import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { loadInternalData } from "./utils/api";
import { RuntimeAgentStreamResponse, streamAgentRun } from "./utils/stream";

vi.mock("./utils/api", () => ({
  loadInternalData: vi.fn(),
}));

vi.mock("./utils/stream", () => ({
  streamAgentRun: vi.fn(),
}));

const mockedLoadInternalData = vi.mocked(loadInternalData);
const mockedStreamAgentRun = vi.mocked(streamAgentRun);

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
      expect(screen.getByText("Loaded 2 documents and created 8 chunks.")).toBeInTheDocument();
    });
  });

  it("shows processing readout indicators while load and run are in flight", async () => {
    const loadDeferred = createDeferred<Awaited<ReturnType<typeof loadInternalData>>>();
    const runDeferred = createDeferred<Awaited<ReturnType<typeof streamAgentRun>>>();
    mockedLoadInternalData.mockImplementation(async () => loadDeferred.promise);
    mockedStreamAgentRun.mockImplementation(async () => runDeferred.promise);

    render(<App />);
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
});
