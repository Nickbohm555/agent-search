import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BenchmarkRunList from "./BenchmarkRunList";

describe("BenchmarkRunList", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads benchmark runs and displays KPI/history columns", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            runs: [
              {
                run_id: "run-completed",
                status: "completed",
                dataset_id: "internal_v1",
                modes: ["agentic_default"],
                created_at: 1700000000,
                started_at: 1700000010,
                finished_at: 1700000070,
              },
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            run_id: "run-completed",
            status: "completed",
            dataset_id: "internal_v1",
            modes: ["agentic_default"],
            objective: {
              primary_kpi: "correctness",
              secondary_kpi: "latency",
              execution_mode: "manual_only",
              targets: {
                min_correctness: 0.75,
                max_latency_ms_p95: 30000,
                max_cost_usd: 5.0,
              },
            },
            targets: null,
            mode_summaries: [],
            results: [
              {
                mode: "agentic_default",
                question_id: "Q1",
                latency_ms: 1200,
                execution_error: null,
                quality: { passed: true },
              },
              {
                mode: "agentic_default",
                question_id: "Q2",
                latency_ms: 1800,
                execution_error: null,
                quality: { passed: true },
              },
            ],
            completed_questions: 2,
            total_questions: 2,
            created_at: 1700000000,
            started_at: 1700000010,
            finished_at: 1700000070,
            error: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    render(<BenchmarkRunList />);

    fireEvent.click(screen.getByRole("button", { name: "Refresh History" }));

    expect(await screen.findByText("Status: Loaded 1 run(s).")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Benchmark run history table" })).toBeInTheDocument();
    expect(screen.getByText("run-completed")).toBeInTheDocument();
    expect(screen.getByText("internal_v1")).toBeInTheDocument();
    expect(screen.getByText("agentic_default")).toBeInTheDocument();
    expect(screen.getByText("100.0%")).toBeInTheDocument();
    expect(screen.getByText("1.8 s")).toBeInTheDocument();
    expect(screen.getByText("Pass")).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(1, "http://localhost:8000/api/benchmarks/runs", expect.any(Object));
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "http://localhost:8000/api/benchmarks/runs/run-completed",
        expect.any(Object),
      );
    });
  });

  it("shows error message when run list request fails", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response("boom", { status: 500 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<BenchmarkRunList />);
    fireEvent.click(screen.getByRole("button", { name: "Refresh History" }));

    expect(await screen.findByText("Status: Failed (Request failed with status 500)")).toBeInTheDocument();
    expect(screen.getByText("No benchmark runs to display.")).toBeInTheDocument();
  });
});
