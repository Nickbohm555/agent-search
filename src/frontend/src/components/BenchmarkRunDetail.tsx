import { FormEvent, useMemo, useState } from "react";

import {
  BenchmarkModeComparison,
  BenchmarkResultStatusItem,
  BenchmarkRunCompareResponse,
  BenchmarkRunStatusResponse,
  getBenchmarkRunCompare,
  getBenchmarkRunStatus,
} from "../utils/api";

type DetailLoadState = "idle" | "loading" | "success" | "error";

export default function BenchmarkRunDetail() {
  const [runIdInput, setRunIdInput] = useState("");
  const [activeRunId, setActiveRunId] = useState("");
  const [statusData, setStatusData] = useState<BenchmarkRunStatusResponse | null>(null);
  const [compareData, setCompareData] = useState<BenchmarkRunCompareResponse | null>(null);
  const [loadState, setLoadState] = useState<DetailLoadState>("idle");
  const [message, setMessage] = useState("Enter a run id to inspect.");

  const comparisonByMode = useMemo(() => {
    if (!compareData) return new Map<string, BenchmarkModeComparison>();
    return new Map(compareData.comparisons.map((item) => [item.mode, item]));
  }, [compareData]);

  async function handleLoad(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (loadState === "loading") return;

    const runId = runIdInput.trim();
    if (!runId) {
      setLoadState("error");
      setMessage("Run id is required.");
      console.warn("Benchmark run detail load blocked: run id missing.");
      return;
    }

    setLoadState("loading");
    setMessage(`Loading detail for ${runId}...`);
    setActiveRunId(runId);
    console.info("Benchmark run detail load started.", { runId });

    const [statusResult, compareResult] = await Promise.all([
      getBenchmarkRunStatus(runId),
      getBenchmarkRunCompare(runId),
    ]);

    if (!statusResult.ok || !compareResult.ok) {
      const errorMessage = [statusResult, compareResult]
        .filter((item) => !item.ok)
        .map((item) => (item.ok ? "" : item.error.message))
        .filter(Boolean)
        .join(" | ");
      setStatusData(null);
      setCompareData(null);
      setLoadState("error");
      setMessage(errorMessage || "Failed to load benchmark detail.");
      console.error("Benchmark run detail load failed.", {
        runId,
        statusError: statusResult.ok ? null : statusResult.error,
        compareError: compareResult.ok ? null : compareResult.error,
      });
      return;
    }

    setStatusData(statusResult.data);
    setCompareData(compareResult.data);
    setLoadState("success");
    setMessage(`Loaded detail for ${runId}.`);
    console.info("Benchmark run detail load completed.", {
      runId,
      modeCount: statusResult.data.mode_summaries.length,
      resultCount: statusResult.data.results.length,
    });
  }

  const hasData = statusData !== null && compareData !== null;

  return (
    <section className="panel benchmark-run-detail-panel">
      <div className="benchmark-run-list-header">
        <h2>Benchmark Run Detail</h2>
      </div>

      <form className="benchmark-run-detail-form" onSubmit={handleLoad}>
        <label htmlFor="benchmark-run-detail-id">Run ID</label>
        <div className="row">
          <input
            id="benchmark-run-detail-id"
            className="benchmark-run-detail-input"
            value={runIdInput}
            onChange={(event) => setRunIdInput(event.target.value)}
            placeholder="e.g. run-123"
            disabled={loadState === "loading"}
          />
          <button type="submit" disabled={loadState === "loading"}>
            {loadState === "loading" ? "Loading..." : "Load Detail"}
          </button>
        </div>
      </form>

      <p>
        Detail status: {loadState === "idle" ? "Not loaded." : message}
      </p>

      {hasData ? (
        <>
          <p>
            Run: <strong>{activeRunId}</strong> | Baseline mode: <strong>{compareData.baseline_mode}</strong>
          </p>
          <div className="benchmark-run-list-table-wrap">
            <table className="benchmark-run-list-table" aria-label="Benchmark mode scorecards">
              <thead>
                <tr>
                  <th>Mode</th>
                  <th>Completed</th>
                  <th>Correctness</th>
                  <th>Delta vs Baseline</th>
                  <th>P95 Latency</th>
                  <th>Latency Delta</th>
                </tr>
              </thead>
              <tbody>
                {statusData.mode_summaries.map((summary) => {
                  const comparison = comparisonByMode.get(summary.mode);
                  return (
                    <tr key={summary.mode}>
                      <td>{summary.mode}</td>
                      <td>
                        {summary.completed_questions}/{summary.total_questions}
                      </td>
                      <td>{formatCorrectness(summary.correctness_rate ?? null)}</td>
                      <td>{formatDeltaPercent(comparison?.correctness_delta ?? null)}</td>
                      <td>{formatLatency(summary.p95_latency_ms ?? null)}</td>
                      <td>{formatDeltaLatency(comparison?.p95_latency_delta_ms ?? null)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="benchmark-run-list-table-wrap">
            <table className="benchmark-run-list-table" aria-label="Benchmark question outcomes table">
              <thead>
                <tr>
                  <th>Mode</th>
                  <th>Question ID</th>
                  <th>Correct</th>
                  <th>Latency</th>
                  <th>Error Status</th>
                </tr>
              </thead>
              <tbody>
                {toSortedRows(statusData.results).map((result) => (
                  <tr key={`${result.mode}-${result.question_id}`}>
                    <td>{result.mode}</td>
                    <td>{result.question_id}</td>
                    <td>{toCorrectnessLabel(result)}</td>
                    <td>{formatLatency(result.latency_ms ?? null)}</td>
                    <td>{result.execution_error?.trim() || "none"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  );
}

function toSortedRows(results: BenchmarkResultStatusItem[]): BenchmarkResultStatusItem[] {
  return [...results].sort((a, b) => {
    if (a.mode !== b.mode) return a.mode.localeCompare(b.mode);
    return a.question_id.localeCompare(b.question_id);
  });
}

function toCorrectnessLabel(result: BenchmarkResultStatusItem): string {
  if (result.quality?.passed === true) return "pass";
  if (result.quality?.passed === false) return "fail";
  return "unknown";
}

function formatCorrectness(value: number | null): string {
  if (value === null) return "n/a";
  return `${(value * 100).toFixed(1)}%`;
}

function formatDeltaPercent(value: number | null): string {
  if (value === null) return "n/a";
  const pct = value * 100;
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(1)} pts`;
}

function formatLatency(value: number | null): string {
  if (value === null) return "n/a";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(1)} s`;
}

function formatDeltaLatency(value: number | null): string {
  if (value === null) return "n/a";
  if (Math.abs(value) < 1000) return `${value >= 0 ? "+" : ""}${Math.round(value)} ms`;
  return `${value >= 0 ? "+" : ""}${(value / 1000).toFixed(1)} s`;
}
