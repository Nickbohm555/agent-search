import { useState } from "react";

import {
  BenchmarkResultStatusItem,
  BenchmarkRunLifecycleStatus,
  BenchmarkRunListItem,
  BenchmarkTargets,
  getBenchmarkRunStatus,
  listBenchmarkRuns,
} from "../utils/api";

type PassFailState = "pass" | "fail" | "in_progress" | "unknown";

type EnrichedBenchmarkRunRow = BenchmarkRunListItem & {
  correctnessRate: number | null;
  p95LatencyMs: number | null;
  startedAt: number | null;
  durationMs: number | null;
  passFail: PassFailState;
};

export default function BenchmarkRunList() {
  const [rows, setRows] = useState<EnrichedBenchmarkRunRow[]>([]);
  const [loadState, setLoadState] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState<string>("");

  async function handleRefresh(): Promise<void> {
    if (loadState === "loading") return;
    setLoadState("loading");
    setErrorMessage("");
    console.info("Benchmark run list refresh started.");

    const listResult = await listBenchmarkRuns();
    if (!listResult.ok) {
      setLoadState("error");
      setErrorMessage(listResult.error.message);
      console.error("Benchmark run list fetch failed.", {
        errorType: listResult.error.type,
        errorMessage: listResult.error.message,
      });
      return;
    }

    const listRows = listResult.data.runs;
    console.info("Benchmark run list base rows loaded.", { runCount: listRows.length });
    const statusResults = await Promise.all(
      listRows.map(async (run) => ({ run, statusResult: await getBenchmarkRunStatus(run.run_id) })),
    );

    const enrichedRows = statusResults.map(({ run, statusResult }) => {
      if (!statusResult.ok) {
        console.warn("Benchmark run status enrichment failed.", {
          runId: run.run_id,
          errorType: statusResult.error.type,
          errorMessage: statusResult.error.message,
        });
        return {
          ...run,
          correctnessRate: null,
          p95LatencyMs: null,
          startedAt: run.started_at ?? run.created_at ?? null,
          durationMs: calculateDurationMs(run.started_at ?? run.created_at ?? null, run.finished_at ?? null),
          passFail: toPassFailState(run.status, null, null, null),
        };
      }

      const status = statusResult.data;
      const computed = computeRunMetrics(status.results);
      const thresholds = status.targets ?? status.objective.targets ?? null;
      const startedAt = status.started_at ?? status.created_at ?? run.started_at ?? run.created_at ?? null;
      const finishedAt = status.finished_at ?? run.finished_at ?? null;
      return {
        ...run,
        correctnessRate: computed.correctnessRate,
        p95LatencyMs: computed.p95LatencyMs,
        startedAt,
        durationMs: calculateDurationMs(startedAt, finishedAt),
        passFail: toPassFailState(run.status, computed.correctnessRate, computed.p95LatencyMs, thresholds),
      };
    });

    setRows(enrichedRows);
    setLoadState("success");
    console.info("Benchmark run list refresh completed.", { runCount: enrichedRows.length });
  }

  return (
    <section className="panel benchmark-run-list-panel">
      <div className="benchmark-run-list-header">
        <h2>Benchmark Runs</h2>
        <button type="button" onClick={handleRefresh} disabled={loadState === "loading"}>
          {loadState === "loading" ? "Refreshing..." : "Refresh History"}
        </button>
      </div>
      <p>
        Status:{" "}
        {loadState === "loading"
          ? "Loading benchmark runs..."
          : loadState === "error"
            ? `Failed (${errorMessage})`
            : loadState === "success"
              ? `Loaded ${rows.length} run(s).`
              : "Not loaded."}
      </p>

      {rows.length === 0 ? (
        <p>No benchmark runs to display.</p>
      ) : (
        <div className="benchmark-run-list-table-wrap">
          <table className="benchmark-run-list-table" aria-label="Benchmark run history table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Run ID</th>
                <th>Dataset</th>
                <th>Modes</th>
                <th>Correctness</th>
                <th>P95 Latency</th>
                <th>Start Time</th>
                <th>Duration</th>
                <th>Threshold</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.run_id}>
                  <td>{row.status}</td>
                  <td>{row.run_id}</td>
                  <td>{row.dataset_id}</td>
                  <td>{row.modes.join(", ") || "n/a"}</td>
                  <td>{formatCorrectness(row.correctnessRate)}</td>
                  <td>{formatLatency(row.p95LatencyMs)}</td>
                  <td>{formatDateTime(row.startedAt)}</td>
                  <td>{formatDuration(row.durationMs)}</td>
                  <td>
                    <span className={`benchmark-pass-badge benchmark-pass-badge-${row.passFail}`}>
                      {toPassFailLabel(row.passFail)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function computeRunMetrics(results: BenchmarkResultStatusItem[]): { correctnessRate: number | null; p95LatencyMs: number | null } {
  if (!Array.isArray(results) || results.length === 0) {
    return { correctnessRate: null, p95LatencyMs: null };
  }

  const total = results.length;
  const passedCount = results.reduce((sum, item) => sum + (item.quality?.passed === true ? 1 : 0), 0);
  const latencies = results
    .filter((item) => !item.execution_error && typeof item.latency_ms === "number")
    .map((item) => item.latency_ms as number);

  return {
    correctnessRate: total > 0 ? passedCount / total : null,
    p95LatencyMs: percentile(latencies, 95),
  };
}

function percentile(values: number[], percentileValue: number): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const clampedPercentile = Math.min(100, Math.max(0, percentileValue));
  const index = Math.ceil((clampedPercentile / 100) * sorted.length) - 1;
  const safeIndex = Math.min(sorted.length - 1, Math.max(0, index));
  return sorted[safeIndex];
}

function toPassFailState(
  status: BenchmarkRunLifecycleStatus,
  correctnessRate: number | null,
  p95LatencyMs: number | null,
  targets: BenchmarkTargets | null,
): PassFailState {
  if (status === "running" || status === "queued" || status === "cancelling") return "in_progress";
  if (status === "failed" || status === "cancelled") return "fail";
  if (!targets || correctnessRate === null || p95LatencyMs === null) return "unknown";
  return correctnessRate >= targets.min_correctness && p95LatencyMs <= targets.max_latency_ms_p95 ? "pass" : "fail";
}

function calculateDurationMs(startedAt: number | null, finishedAt: number | null): number | null {
  if (startedAt === null) return null;
  const end = finishedAt ?? Math.floor(Date.now() / 1000);
  return Math.max(0, Math.round((end - startedAt) * 1000));
}

function formatDateTime(timestamp: number | null): string {
  if (timestamp === null) return "n/a";
  return new Date(timestamp * 1000).toLocaleString();
}

function formatCorrectness(value: number | null): string {
  if (value === null) return "n/a";
  return `${(value * 100).toFixed(1)}%`;
}

function formatLatency(value: number | null): string {
  if (value === null) return "n/a";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(1)} s`;
}

function formatDuration(value: number | null): string {
  if (value === null) return "n/a";
  if (value < 1000) return `${value} ms`;
  const seconds = value / 1000;
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

function toPassFailLabel(value: PassFailState): string {
  if (value === "pass") return "Pass";
  if (value === "fail") return "Fail";
  if (value === "in_progress") return "Running";
  return "Unknown";
}
