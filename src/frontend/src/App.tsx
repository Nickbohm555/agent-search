import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  RuntimeAgentGraphStep,
  RuntimeAgentRunResponse,
  WikiSourceOption,
  listWikiSources,
  loadInternalData,
  wipeInternalData,
} from "./utils/api";
import { RuntimeAgentStreamCompletedData, RuntimeAgentStreamEvent } from "./lib/stream-events";
import { SAMPLE_INTERNAL_DOCUMENTS } from "./lib/constants";
import { ProgressHistory } from "./lib/components/ProgressHistory";
import { QueryForm } from "./lib/components/QueryForm";
import { StatusBanner } from "./lib/components/StatusBanner";
import { RequestState } from "./lib/types";
import { formatLoadSuccessMessage, formatRunSuccessMessage } from "./lib/utils/messages";
import { usePrefersReducedMotion } from "./utils/motion";
import { streamAgentRun } from "./utils/stream";

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isSubQueryRetrievalResult(value: unknown): value is RuntimeAgentRunResponse["retrieval_results"][number] {
  if (!isObject(value)) {
    return false;
  }

  return (
    typeof value.sub_query === "string" &&
    (value.tool === "internal" || value.tool === "web") &&
    Array.isArray(value.internal_results) &&
    Array.isArray(value.web_search_results) &&
    Array.isArray(value.opened_urls) &&
    Array.isArray(value.opened_pages)
  );
}

function isSubQueryValidationResult(value: unknown): value is RuntimeAgentRunResponse["validation_results"][number] {
  if (!isObject(value)) {
    return false;
  }

  return (
    typeof value.sub_query === "string" &&
    (value.tool === "internal" || value.tool === "web") &&
    typeof value.sufficient === "boolean" &&
    (value.status === "validated" || value.status === "stopped_insufficient") &&
    typeof value.attempts === "number" &&
    Array.isArray(value.follow_up_actions) &&
    typeof value.stop_reason === "string"
  );
}

function deriveRunDetailsFromStream(
  streamEvents: RuntimeAgentStreamEvent[],
  completed: RuntimeAgentStreamCompletedData,
  streamProgressBuffer: RuntimeAgentGraphStep[],
): RuntimeAgentRunResponse {
  // Called by `handleRun` after a successful stream so final readouts preserve
  // retrieval/validation details observed in-flight instead of defaulting to
  // empty lists when only completed payload fields are available.
  const retrievalResults: RuntimeAgentRunResponse["retrieval_results"] = [];
  const validationResults: RuntimeAgentRunResponse["validation_results"] = [];

  for (const event of streamEvents) {
    if (event.event === "retrieval_result" && isSubQueryRetrievalResult(event.data)) {
      retrievalResults.push(event.data);
      continue;
    }

    if (event.event === "validation_result" && isSubQueryValidationResult(event.data)) {
      validationResults.push(event.data);
    }
  }
  const webToolRuns = retrievalResults
    .filter((result) => result.tool === "web")
    .map((result) => ({
      sub_query: result.sub_query,
      search_results: result.web_search_results,
      opened_urls: result.opened_urls,
      opened_pages: result.opened_pages,
    }));

  return {
    agent_name: completed.agent_name,
    output: completed.output,
    thread_id: completed.thread_id,
    checkpoint_id: completed.checkpoint_id ?? null,
    sub_queries: completed.sub_queries,
    tool_assignments: completed.tool_assignments,
    retrieval_results: retrievalResults,
    validation_results: validationResults,
    web_tool_runs: webToolRuns,
    graph_state: {
      current_step:
        streamProgressBuffer.length > 0
          ? streamProgressBuffer[streamProgressBuffer.length - 1].step
          : "completed",
      timeline: [...streamProgressBuffer],
      graph: {},
    },
  };
}

export default function App() {
  const prefersReducedMotion = usePrefersReducedMotion();
  const [loadState, setLoadState] = useState<RequestState>("idle");
  const [loadMessage, setLoadMessage] = useState("Not started.");
  const [loadSourceType, setLoadSourceType] = useState<"inline" | "wiki">("wiki");
  const [wikiSources, setWikiSources] = useState<WikiSourceOption[]>([]);
  const [wikiSourceId, setWikiSourceId] = useState("");
  const [query, setQuery] = useState("");
  const [runState, setRunState] = useState<RequestState>("idle");
  const [runMessage, setRunMessage] = useState("Waiting for query.");
  const [answer, setAnswer] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [runDetails, setRunDetails] = useState<RuntimeAgentRunResponse | null>(null);
  const [streamedProgress, setStreamedProgress] = useState<RuntimeAgentGraphStep[]>([]);
  const [streamedSubQueries, setStreamedSubQueries] = useState<string[]>([]);
  const [streamedToolAssignments, setStreamedToolAssignments] = useState<RuntimeAgentRunResponse["tool_assignments"]>(
    [],
  );
  const loadInFlightRef = useRef(false);
  const [wipeState, setWipeState] = useState<RequestState>("idle");
  const [wipeMessage, setWipeMessage] = useState("");
  const wipeInFlightRef = useRef(false);
  const runInFlightRef = useRef(false);

  const isRunDisabled = useMemo(() => runState === "loading" || query.trim().length === 0, [runState, query]);
  const isWikiLoad = loadSourceType === "wiki";
  const selectedWikiSource = useMemo(
    () => wikiSources.find((source) => source.source_id === wikiSourceId) ?? null,
    [wikiSourceId, wikiSources],
  );
  const isLoadDisabled = useMemo(() => {
    if (loadState === "loading") {
      return true;
    }
    return isWikiLoad && (!selectedWikiSource || selectedWikiSource.already_loaded);
  }, [isWikiLoad, loadState, selectedWikiSource]);

  useEffect(() => {
    let isMounted = true;
    async function loadWikiSources() {
      const result = await listWikiSources();
      if (!isMounted || !result.ok) {
        return;
      }
      setWikiSources(result.data.sources);
      if (result.data.sources.length > 0) {
        setWikiSourceId((previous) => previous || result.data.sources[0].source_id);
      }
    }
    loadWikiSources();
    return () => {
      isMounted = false;
    };
  }, []);

  function buildLoadPayload() {
    // Called by `handleLoad` so the load action can preserve inline compatibility
    // while supporting wiki-triggered ingestion from the same control surface.
    if (isWikiLoad) {
      return {
        source_type: "wiki" as const,
        wiki: { source_id: wikiSourceId },
      };
    }

    return {
      source_type: "inline" as const,
      documents: SAMPLE_INTERNAL_DOCUMENTS,
    };
  }

  async function handleLoad(): Promise<void> {
    if (loadInFlightRef.current) {
      return;
    }
    loadInFlightRef.current = true;
    setLoadState("loading");
    setLoadMessage("Loading and vectorizing internal docs...");

    if (isWikiLoad && selectedWikiSource?.already_loaded) {
      setLoadState("error");
      setLoadMessage(`"${selectedWikiSource.label}" is already loaded.`);
      loadInFlightRef.current = false;
      return;
    }

    try {
      const result = await loadInternalData(buildLoadPayload());

      if (result.ok) {
        setLoadState("success");
        setLoadMessage(
          formatLoadSuccessMessage(result.data.source_type, result.data.documents_loaded, result.data.chunks_created),
        );
        if (isWikiLoad && selectedWikiSource) {
          setWikiSources((existing) =>
            existing.map((source) =>
              source.source_id === selectedWikiSource.source_id ? { ...source, already_loaded: true } : source,
            ),
          );
        }
        return;
      }

      setLoadState("error");
      setLoadMessage(result.error.message);
    } finally {
      loadInFlightRef.current = false;
    }
  }

  /**
   * Called by the load/vectorize form submit path so keyboard users can trigger
   * the same load behavior as pointer users without duplicating load logic.
   * Side effects: prevents browser form navigation and delegates to `handleLoad`.
   */
  async function handleLoadSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    await handleLoad();
  }

  async function handleWipe(): Promise<void> {
    if (wipeInFlightRef.current) return;
    wipeInFlightRef.current = true;
    setWipeState("loading");
    setWipeMessage("Wiping...");
    try {
      const result = await wipeInternalData();
      if (result.ok) {
        setWipeState("success");
        setWipeMessage(result.data.message);
        const sourcesResult = await listWikiSources();
        if (sourcesResult.ok) setWikiSources(sourcesResult.data.sources);
      } else {
        setWipeState("error");
        setWipeMessage(result.error.message);
      }
    } finally {
      wipeInFlightRef.current = false;
    }
  }

  function applyStreamEvent(
    event: RuntimeAgentStreamEvent,
    progress: RuntimeAgentGraphStep[],
    subQueries: string[],
    toolAssignments: RuntimeAgentRunResponse["tool_assignments"],
  ): void {
    // Called by `handleRun` for each streamed event so the UI can update readouts
    // before completion without waiting for the entire stream response.
    // Side effects: updates in-flight progress, sub-query, and tool-assignment
    // state buffers that `ProgressHistory` renders during stream execution.
    if (event.event === "heartbeat") {
      setRunMessage(`Heartbeat: ${event.data.status}`);
      return;
    }

    if (event.event === "progress") {
      const timelineEntry: RuntimeAgentGraphStep = {
        step: event.data.step,
        status: event.data.status === "completed" ? "completed" : "started",
        details: {},
      };
      progress.push(timelineEntry);
      setStreamedProgress([...progress]);
      setRunMessage(`Step ${event.data.step}: ${event.data.status}`);
      return;
    }

    if (event.event === "sub_queries") {
      subQueries.splice(0, subQueries.length, ...event.data.sub_queries);
      setStreamedSubQueries([...subQueries]);
      setRunMessage(`Generated ${event.data.count} sub-queries.`);
      return;
    }

    if (event.event === "tool_assignments") {
      toolAssignments.splice(0, toolAssignments.length, ...event.data.tool_assignments);
      setStreamedToolAssignments([...toolAssignments]);
      setRunMessage(`Assigned tools for ${event.data.count} sub-queries.`);
    }
  }

  async function handleRun(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (query.trim().length === 0 || runInFlightRef.current) {
      return;
    }

    runInFlightRef.current = true;
    const trimmedQuery = query.trim();
    const streamProgressBuffer: RuntimeAgentGraphStep[] = [];
    const streamSubQueryBuffer: string[] = [];
    const streamToolAssignmentsBuffer: RuntimeAgentRunResponse["tool_assignments"] = [];

    setRunState("loading");
    setRunMessage("Running agent stream...");
    setAnswer("");
    setRunDetails(null);
    setStreamedProgress([]);
    setStreamedSubQueries([]);
    setStreamedToolAssignments([]);
    setSubmittedQuery(trimmedQuery);

    try {
      const result = await streamAgentRun(
        { query: trimmedQuery },
        {
          onEvent: (streamEvent) => {
            applyStreamEvent(
              streamEvent,
              streamProgressBuffer,
              streamSubQueryBuffer,
              streamToolAssignmentsBuffer,
            );
          },
        },
      );

      if (result.ok) {
        setStreamedProgress([...streamProgressBuffer]);
        setStreamedSubQueries([...result.data.completed.sub_queries]);
        setStreamedToolAssignments([...result.data.completed.tool_assignments]);
        setRunState("success");
        setRunMessage(formatRunSuccessMessage(result.data.completed.sub_queries.length));
        setAnswer(result.data.completed.output);
        setRunDetails(
          deriveRunDetailsFromStream(result.data.events, result.data.completed, streamProgressBuffer),
        );
        return;
      }

      setRunState("error");
      setRunMessage(result.error.message);
    } finally {
      runInFlightRef.current = false;
    }
  }

  return (
    <main
      className={`container theme-cyberpunk deck-shell${prefersReducedMotion ? " reduced-motion" : ""}`}
      data-theme="cyberpunk"
      data-reduced-motion={prefersReducedMotion ? "true" : "false"}
    >
      <header className="deck-header">
        <h1>Agent Search Demo</h1>
        <p className="lead">Load internal docs, run a query, and review the synthesized answer.</p>
      </header>

      <div className="deck-grid">
        <section className="card deck-panel deck-controls" aria-label="controls" data-testid="controls-panel">
          <div className="panel-titlebar">
            <h2>Control Deck</h2>
            <span className="panel-kicker">ACTION</span>
          </div>

          <form className="control-block" onSubmit={handleLoadSubmit}>
            <h3>Load / Vectorize</h3>
            <p>Load sample docs or a wiki topic for retrieval.</p>
            <label htmlFor="load-source">Load Source</label>
            <select
              id="load-source"
              value={loadSourceType}
              onChange={(event) => setLoadSourceType(event.target.value as "inline" | "wiki")}
              disabled={loadState === "loading"}
            >
              <option value="inline">Sample Inline Docs</option>
              <option value="wiki">Wiki Topic</option>
            </select>
            {isWikiLoad ? (
              <>
                <label htmlFor="wiki-source-id">Wiki Source</label>
                <select
                  id="wiki-source-id"
                  value={wikiSourceId}
                  onChange={(event) => setWikiSourceId(event.target.value)}
                  disabled={loadState === "loading"}
                >
                  {wikiSources.map((source) => (
                    <option key={source.source_id} value={source.source_id}>
                      {source.label}
                      {source.already_loaded ? " (loaded)" : ""}
                    </option>
                  ))}
                </select>
                {selectedWikiSource?.already_loaded ? (
                  <p role="status">Selected wiki source is already loaded. Choose another source.</p>
                ) : null}
              </>
            ) : null}
            <button
              type="submit"
              className="action-button neon-action"
              disabled={isLoadDisabled}
            >
              {loadState === "loading" ? "Loading..." : "Load Data"}
            </button>
            <StatusBanner state={loadState} message={loadMessage} label="Load Status" testId="load-status-region" />
            <div className="control-block">
              <button
                type="button"
                className="action-button"
                onClick={handleWipe}
                disabled={wipeState === "loading"}
                aria-label="Wipe all internal documents and chunks"
              >
                {wipeState === "loading" ? "Wiping..." : "Wipe data"}
              </button>
              {wipeMessage ? <p role="status">{wipeMessage}</p> : null}
            </div>
          </form>

          <div className="control-block">
            <h3>Run Query</h3>
            <QueryForm
              query={query}
              onQueryChange={setQuery}
              onSubmit={handleRun}
              isRunDisabled={isRunDisabled}
              isLoading={runState === "loading"}
            />
          </div>
        </section>

        <section className="card deck-panel deck-progress" aria-label="progress" data-testid="progress-panel">
          <div className="panel-titlebar">
            <h2>System Progress</h2>
            <span className="panel-kicker">READOUT</span>
          </div>
          <StatusBanner state={runState} message={runMessage} label="Run Status" testId="progress-region" />
          <ProgressHistory
            runDetails={runDetails}
            streamedProgress={streamedProgress}
            streamedSubQueries={streamedSubQueries}
            streamedToolAssignments={streamedToolAssignments}
          />
        </section>

        <section className="card deck-panel deck-result" aria-label="result" data-testid="result-panel">
          <div className="panel-titlebar">
            <h2>Final Readout</h2>
            <span className="panel-kicker">ANSWER</span>
          </div>
          <div className="query-readout readout-block" data-testid="query-readout">
            <p className="readout-label">Requested Query</p>
            <p className="readout-value">{submittedQuery || "No query submitted yet."}</p>
          </div>
          <div className="answer answer-dominant readout-block" aria-live="polite" data-testid="final-answer-region">
            <h3>Final Answer</h3>
            {answer ? <p>{answer}</p> : <p>No answer yet.</p>}
          </div>
        </section>
      </div>
    </main>
  );
}
