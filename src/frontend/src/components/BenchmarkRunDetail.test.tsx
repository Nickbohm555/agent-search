import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BenchmarkRunDetail from "./BenchmarkRunDetail";

describe("BenchmarkRunDetail", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("loads run detail and renders mode deltas and question outcomes", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            run_id: "run-42",
            status: "completed",
            dataset_id: "internal_v1",
            modes: ["baseline_retrieve_then_answer", "agentic_default"],
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
            mode_summaries: [
              {
                mode: "baseline_retrieve_then_answer",
                completed_questions: 2,
                total_questions: 2,
                correctness_rate: 0.5,
                p95_latency_ms: 2400,
              },
              {
                mode: "agentic_default",
                completed_questions: 2,
                total_questions: 2,
                correctness_rate: 1.0,
                p95_latency_ms: 1800,
              },
            ],
            results: [
              {
                mode: "agentic_default",
                question_id: "Q2",
                latency_ms: 1300,
                execution_error: null,
                quality: { passed: true, score: 0.91 },
              },
              {
                mode: "baseline_retrieve_then_answer",
                question_id: "Q1",
                latency_ms: 2200,
                execution_error: "timeout",
                quality: { passed: false, score: 0.22 },
              },
            ],
            completed_questions: 4,
            total_questions: 4,
            created_at: 1700000000,
            started_at: 1700000010,
            finished_at: 1700000070,
            error: null,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            run_id: "run-42",
            baseline_mode: "baseline_retrieve_then_answer",
            comparisons: [
              {
                mode: "baseline_retrieve_then_answer",
                correctness_rate: 0.5,
                correctness_delta: 0,
                p95_latency_ms: 2400,
                p95_latency_delta_ms: 0,
              },
              {
                mode: "agentic_default",
                correctness_rate: 1.0,
                correctness_delta: 0.5,
                p95_latency_ms: 1800,
                p95_latency_delta_ms: -600,
              },
            ],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    vi.stubGlobal("fetch", fetchMock);

    render(<BenchmarkRunDetail />);

    fireEvent.change(screen.getByLabelText("Run ID"), { target: { value: "run-42" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Detail" }));

    expect(await screen.findByText("Detail status: Loaded detail for run-42.")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Benchmark mode scorecards" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Benchmark question outcomes table" })).toBeInTheDocument();
    expect(screen.getByText("+50.0 pts")).toBeInTheDocument();
    expect(screen.getByText("-600 ms")).toBeInTheDocument();
    expect(screen.getByText("pass")).toBeInTheDocument();
    expect(screen.getByText("fail")).toBeInTheDocument();
    expect(screen.getByText("timeout")).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(1, "http://localhost:8000/api/benchmarks/runs/run-42", expect.any(Object));
    });
    await waitFor(() => {
      expect(fetchMock).toHaveBeenNthCalledWith(
        2,
        "http://localhost:8000/api/benchmarks/runs/run-42/compare",
        expect.any(Object),
      );
    });
  });

  it("shows an error when detail requests fail", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("not found", { status: 404 }))
      .mockResolvedValueOnce(new Response("not found", { status: 404 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<BenchmarkRunDetail />);

    fireEvent.change(screen.getByLabelText("Run ID"), { target: { value: "missing-run" } });
    fireEvent.click(screen.getByRole("button", { name: "Load Detail" }));

    expect(await screen.findByText(/Detail status: Request failed with status 404/)).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Benchmark mode scorecards" })).not.toBeInTheDocument();
  });
});
