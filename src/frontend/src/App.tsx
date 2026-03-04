import { FormEvent, useMemo, useRef, useState } from "react";
import { RuntimeAgentRunResponse, loadInternalData, runAgentStream } from "./utils/api";
import { SAMPLE_INTERNAL_DOCUMENTS } from "./lib/constants";
import { ProgressHistory } from "./lib/components/ProgressHistory";
import { QueryForm } from "./lib/components/QueryForm";
import { StatusBanner } from "./lib/components/StatusBanner";
import { RequestState } from "./lib/types";
import { formatHeartbeatMessage, formatLoadSuccessMessage, formatRunSuccessMessage } from "./lib/utils/messages";

export default function App() {
  const [loadState, setLoadState] = useState<RequestState>("idle");
  const [loadMessage, setLoadMessage] = useState("Not started.");
  const [query, setQuery] = useState("");
  const [runState, setRunState] = useState<RequestState>("idle");
  const [runMessage, setRunMessage] = useState("Waiting for query.");
  const [answer, setAnswer] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [runDetails, setRunDetails] = useState<RuntimeAgentRunResponse | null>(null);
  const loadInFlightRef = useRef(false);
  const runInFlightRef = useRef(false);

  const isRunDisabled = useMemo(() => runState === "loading" || query.trim().length === 0, [runState, query]);

  async function handleLoad(): Promise<void> {
    if (loadInFlightRef.current) {
      return;
    }
    loadInFlightRef.current = true;
    setLoadState("loading");
    setLoadMessage("Loading and vectorizing internal docs...");

    try {
      const result = await loadInternalData({
        source_type: "inline",
        documents: SAMPLE_INTERNAL_DOCUMENTS,
      });

      if (result.ok) {
        setLoadState("success");
        setLoadMessage(formatLoadSuccessMessage(result.data.documents_loaded, result.data.chunks_created));
        return;
      }

      setLoadState("error");
      setLoadMessage(result.error.message);
    } finally {
      loadInFlightRef.current = false;
    }
  }

  async function handleRun(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (query.trim().length === 0 || runInFlightRef.current) {
      return;
    }

    runInFlightRef.current = true;
    const trimmedQuery = query.trim();
    setRunState("loading");
    setRunMessage("Running agent...");
    setAnswer("");
    setRunDetails(null);
    setSubmittedQuery(trimmedQuery);

    try {
      const result = await runAgentStream(
        { query: trimmedQuery },
        {
          onEvent: (event, snapshot) => {
            setRunDetails(snapshot);
            if (snapshot.output) {
              setAnswer(snapshot.output);
            }
            if (event.event === "heartbeat") {
              const timeline = snapshot.graph_state?.timeline;
              const latestEntry = timeline && timeline.length > 0 ? timeline[timeline.length - 1] : null;
              if (latestEntry) {
                setRunMessage(formatHeartbeatMessage(latestEntry.step, latestEntry.status));
              }
              return;
            }
            if (event.event === "sub_queries" && snapshot.sub_queries.length > 0) {
              setRunMessage(`Streaming progress. ${snapshot.sub_queries.length} sub-queries received.`);
            }
          },
        },
      );
      if (result.ok) {
        setRunState("success");
        setRunMessage(formatRunSuccessMessage(result.data.sub_queries.length));
        setAnswer(result.data.output);
        setRunDetails(result.data);
        return;
      }

      setRunState("error");
      setRunMessage(result.error.message);
    } finally {
      runInFlightRef.current = false;
    }
  }

  return (
    <main className="container theme-cyberpunk deck-shell" data-theme="cyberpunk">
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

          <div className="control-block">
            <h3>Load / Vectorize</h3>
            <p>Ingest sample internal docs for retrieval.</p>
            <button
              type="button"
              className="action-button neon-action"
              onClick={handleLoad}
              disabled={loadState === "loading"}
              aria-busy={loadState === "loading"}
            >
              {loadState === "loading" ? "Loading..." : "Load Data"}
            </button>
            <StatusBanner
              state={loadState}
              message={loadMessage}
              label="Load Status"
              testId="load-status-region"
              busy={loadState === "loading"}
            />
          </div>

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
          <StatusBanner
            state={runState}
            message={runMessage}
            label="Run Status"
            testId="progress-region"
            busy={runState === "loading"}
          />
          <ProgressHistory runDetails={runDetails} />
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
