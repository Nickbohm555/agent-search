import { FormEvent, useMemo, useRef, useState } from "react";
import { RuntimeAgentRunResponse, loadInternalData, runAgent } from "./utils/api";
import { SAMPLE_INTERNAL_DOCUMENTS } from "./lib/constants";
import { ProgressHistory } from "./lib/components/ProgressHistory";
import { QueryForm } from "./lib/components/QueryForm";
import { StatusBanner } from "./lib/components/StatusBanner";
import { RequestState } from "./lib/types";
import { formatLoadSuccessMessage, formatRunSuccessMessage } from "./lib/utils/messages";

export default function App() {
  const [loadState, setLoadState] = useState<RequestState>("idle");
  const [loadMessage, setLoadMessage] = useState("Not started.");
  const [query, setQuery] = useState("");
  const [runState, setRunState] = useState<RequestState>("idle");
  const [runMessage, setRunMessage] = useState("Waiting for query.");
  const [answer, setAnswer] = useState("");
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
    setRunState("loading");
    setRunMessage("Running agent...");
    setAnswer("");
    setRunDetails(null);

    try {
      const result = await runAgent({ query: query.trim() });
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
    <main className="container theme-cyberpunk" data-theme="cyberpunk">
      <h1>Agent Search Demo</h1>
      <p className="lead">Load internal docs, run a query, and review the synthesized answer.</p>

      <section className="card">
        <h2>Load / Vectorize</h2>
        <p>Ingest sample internal docs for retrieval.</p>
        <button
          type="button"
          className="action-button neon-action"
          onClick={handleLoad}
          disabled={loadState === "loading"}
        >
          {loadState === "loading" ? "Loading..." : "Load Data"}
        </button>
        <StatusBanner state={loadState} message={loadMessage} testId="load-status-region" />
      </section>

      <section className="card">
        <h2>Run Query</h2>
        <QueryForm
          query={query}
          onQueryChange={setQuery}
          onSubmit={handleRun}
          isRunDisabled={isRunDisabled}
          isLoading={runState === "loading"}
        />

        <StatusBanner state={runState} message={runMessage} testId="progress-region" />

        <div className="answer" aria-live="polite" data-testid="final-answer-region">
          <h3>Final Answer</h3>
          {answer ? <p>{answer}</p> : <p>No answer yet.</p>}
        </div>

        <ProgressHistory runDetails={runDetails} />
      </section>
    </main>
  );
}
