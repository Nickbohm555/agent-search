import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { loadInternalData, runAgent } from "./utils/api";

vi.mock("./utils/api", () => ({
  loadInternalData: vi.fn(),
  runAgent: vi.fn(),
}));

const mockedLoadInternalData = vi.mocked(loadInternalData);
const mockedRunAgent = vi.mocked(runAgent);

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

  it("shows final answer for successful run", async () => {
    mockedRunAgent.mockResolvedValue({
      ok: true,
      data: {
        agent_name: "langgraph-scaffold",
        output: "This is the synthesized answer.",
        sub_queries: ["subquery-a", "subquery-b"],
        tool_assignments: [
          { sub_query: "subquery-a", tool: "internal" },
          { sub_query: "subquery-b", tool: "web" },
        ],
        retrieval_results: [],
        validation_results: [],
        web_tool_runs: [],
        graph_state: null,
      },
    });

    render(<App />);
    fireEvent.change(screen.getByLabelText("Query"), { target: { value: "What is the project status?" } });
    fireEvent.click(screen.getByRole("button", { name: "Run Agent" }));

    await waitFor(() => {
      expect(screen.getByText("This is the synthesized answer.")).toBeInTheDocument();
      expect(screen.getByText("Run complete. 2 sub-queries processed.")).toBeInTheDocument();
    });
  });

  it("shows run failure and preserves query text for retry", async () => {
    mockedRunAgent.mockResolvedValue({
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
});
