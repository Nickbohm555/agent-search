import { FormEvent, useMemo, useState } from "react";
import { RuntimeAgentRunResponse, loadInternalData, runAgent } from "./utils/api";

export default function App() {
  const [loadState, setLoadState] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [loadMessage, setLoadMessage] = useState("Not started.");
  const [query, setQuery] = useState("");
  const [runState, setRunState] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [runMessage, setRunMessage] = useState("Waiting for query.");
  const [answer, setAnswer] = useState("");
  const [runDetails, setRunDetails] = useState<RuntimeAgentRunResponse | null>(null);

  const isRunDisabled = useMemo(() => runState === "loading" || query.trim().length === 0, [runState, query]);

  async function handleLoad(): Promise<void> {
    setLoadState("loading");
    setLoadMessage("Loading and vectorizing internal docs...");

    const result = await loadInternalData({
      source_type: "inline",
      documents: [
        {
          title: "Product Notes",
          content: "Agent Search loads internal data and can retrieve chunked context.",
          source_ref: "demo://product-notes",
        },
        {
          title: "Roadmap",
          content: "The orchestration flow decomposes user queries and synthesizes final answers.",
          source_ref: "demo://roadmap",
        },
      ],
    });

    if (result.ok) {
      setLoadState("success");
      setLoadMessage(
        `Loaded ${result.data.documents_loaded} documents and created ${result.data.chunks_created} chunks.`,
      );
      return;
    }

    setLoadState("error");
    setLoadMessage(result.error.message);
  }

  async function handleRun(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (query.trim().length === 0 || runState === "loading") {
      return;
    }

    setRunState("loading");
    setRunMessage("Running agent...");
    setAnswer("");
    setRunDetails(null);

    const result = await runAgent({ query: query.trim() });
    if (result.ok) {
      setRunState("success");
      setRunMessage(`Run complete. ${result.data.sub_queries.length} sub-queries processed.`);
      setAnswer(result.data.output);
      setRunDetails(result.data);
      return;
    }

    setRunState("error");
    setRunMessage(result.error.message);
  }

  return (
    <main className="container">
      <h1>Agent Search Demo</h1>
      <p className="lead">Load internal docs, run a query, and review the synthesized answer.</p>

      <section className="card">
        <h2>Load / Vectorize</h2>
        <p>Ingest sample internal docs for retrieval.</p>
        <button type="button" onClick={handleLoad} disabled={loadState === "loading"}>
          {loadState === "loading" ? "Loading..." : "Load Data"}
        </button>
        <div className={`status status-${loadState}`} aria-live="polite" data-testid="load-status-region">
          {loadMessage}
        </div>
      </section>

      <section className="card">
        <h2>Run Query</h2>
        <form onSubmit={handleRun}>
          <label htmlFor="query-input">Query</label>
          <textarea
            id="query-input"
            name="query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            rows={3}
            placeholder="Ask a complex question..."
          />
          <button type="submit" disabled={isRunDisabled}>
            {runState === "loading" ? "Running..." : "Run Agent"}
          </button>
        </form>

        <div className={`status status-${runState}`} aria-live="polite" data-testid="progress-region">
          {runMessage}
        </div>

        <div className="answer" aria-live="polite" data-testid="final-answer-region">
          <h3>Final Answer</h3>
          {answer ? <p>{answer}</p> : <p>No answer yet.</p>}
        </div>

        <div className="progress-history" data-testid="progress-history-region">
          <h3>Progress History</h3>
          {runDetails ? (
            <>
              {runDetails.graph_state?.timeline?.length ? (
                <ol data-testid="timeline-list">
                  {runDetails.graph_state.timeline.map((entry, index) => (
                    <li key={`${entry.step}-${index}`}>
                      <strong>{entry.step}</strong>: {entry.status}
                    </li>
                  ))}
                </ol>
              ) : (
                <p data-testid="timeline-empty">No graph timeline available.</p>
              )}

              {runDetails.sub_queries.length ? (
                <ul data-testid="subquery-list">
                  {runDetails.sub_queries.map((subQuery) => {
                    const assignment = runDetails.tool_assignments.find((item) => item.sub_query === subQuery);
                    const toolLabel = assignment ? assignment.tool : "unassigned";
                    return (
                      <li key={subQuery}>
                        {subQuery} ({toolLabel})
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <p data-testid="subquery-empty">No sub-queries were returned.</p>
              )}

              {runDetails.validation_results.length ? (
                <ul data-testid="validation-list">
                  {runDetails.validation_results.map((validation) => (
                    <li key={`${validation.sub_query}-${validation.tool}`}>
                      {validation.sub_query}: {validation.status}
                    </li>
                  ))}
                </ul>
              ) : (
                <p data-testid="validation-empty">No validation results were returned.</p>
              )}
            </>
          ) : (
            <p>No run details yet.</p>
          )}
        </div>
      </section>
    </main>
  );
}
