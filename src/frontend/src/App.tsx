import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  RequestState,
  RuntimeAgentRunResponse,
  WikiSourceOption,
  listWikiSources,
  loadWikiSource,
  runAgent,
  wipeInternalData,
} from "./utils/api";
import { DEFAULT_WIKI_SOURCES } from "./utils/constants";

function runSymbol(state: RequestState): string {
  if (state === "success") return "✓";
  if (state === "error") return "✗";
  if (state === "loading") return "…";
  return "-";
}

export default function App() {
  const [wikiSources, setWikiSources] = useState<WikiSourceOption[]>(DEFAULT_WIKI_SOURCES);
  const [wikiSourceId, setWikiSourceId] = useState(DEFAULT_WIKI_SOURCES[0]?.source_id ?? "");
  const [loadState, setLoadState] = useState<RequestState>("idle");
  const [loadMessage, setLoadMessage] = useState("Not started.");
  const [wipeState, setWipeState] = useState<RequestState>("idle");
  const [wipeMessage, setWipeMessage] = useState("");

  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [runState, setRunState] = useState<RequestState>("idle");
  const [answer, setAnswer] = useState("");
  const [lastRunResponse, setLastRunResponse] = useState<RuntimeAgentRunResponse | null>(null);

  const selectedWikiSource = useMemo(
    () => wikiSources.find((source) => source.source_id === wikiSourceId) ?? null,
    [wikiSources, wikiSourceId],
  );

  useEffect(() => {
    let mounted = true;
    async function init() {
      const result = await listWikiSources();
      if (!mounted || !result.ok) return;
      const mergedSources = mergeWikiSourcesWithFallback(result.data.sources);
      setWikiSources(mergedSources);
      if (mergedSources.length > 0) {
        setWikiSourceId(mergedSources[0].source_id);
      }
    }
    init();
    return () => {
      mounted = false;
    };
  }, []);

  async function handleLoadWiki(): Promise<void> {
    if (!selectedWikiSource || selectedWikiSource.already_loaded || loadState === "loading") return;

    setLoadState("loading");
    setLoadMessage("Loading wiki source...");
    const result = await loadWikiSource(selectedWikiSource.source_id);

    if (result.ok) {
      setLoadState("success");
      setLoadMessage(`Loaded ${result.data.documents_loaded} docs (${result.data.chunks_created} chunks).`);
      const refresh = await listWikiSources();
      if (refresh.ok) setWikiSources(mergeWikiSourcesWithFallback(refresh.data.sources));
      return;
    }

    setLoadState("error");
    setLoadMessage(result.error.message);
  }

  async function handleWipe(): Promise<void> {
    if (wipeState === "loading") return;

    setWipeState("loading");
    setWipeMessage("Wiping data...");
    const result = await wipeInternalData();

    if (result.ok) {
      setWipeState("success");
      setWipeMessage(result.data.message);
      const refresh = await listWikiSources();
      if (refresh.ok) setWikiSources(mergeWikiSourcesWithFallback(refresh.data.sources));
      return;
    }

    setWipeState("error");
    setWipeMessage(result.error.message);
  }

  async function handleRun(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!query.trim() || runState === "loading") return;

    const submitted = query.trim();
    setSubmittedQuery(submitted);
    setRunState("loading");
    setAnswer("");
    setLastRunResponse(null);
    console.info("Run query started.", { submittedQuery: submitted });

    const result = await runAgent(submitted);
    if (result.ok) {
      setRunState("success");
      setAnswer(result.data.output);
      setLastRunResponse(result.data);
      const subQuestionsWithDetails = result.data.sub_qa.filter(
        (item) =>
          item.sub_answer.trim().length > 0 ||
          item.sub_agent_response?.trim().length ||
          item.tool_call_input?.trim().length,
      ).length;
      console.info("Run query completed.", {
        submittedQuery: submitted,
        hasMainQuestion: Boolean(result.data.main_question.trim()),
        subQuestionCount: result.data.sub_qa.length,
        subQuestionsWithDetails,
      });
      return;
    }

    setRunState("error");
    setAnswer(result.error.message);
    console.error("Run query failed.", { submittedQuery: submitted, error: result.error.message });
  }

  return (
    <main className="app-shell">
      <h1>Agent Search</h1>

      <section className="panel">
        <h2>Wiki Data</h2>
        <label htmlFor="wiki-source">Wiki Source</label>
        <select
          id="wiki-source"
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

        <div className="row">
          <button
            type="button"
            onClick={handleLoadWiki}
            disabled={!selectedWikiSource || selectedWikiSource.already_loaded || loadState === "loading"}
          >
            {loadState === "loading" ? "Loading..." : "Load Wiki Source"}
          </button>
          <button type="button" onClick={handleWipe} disabled={wipeState === "loading"}>
            {wipeState === "loading" ? "Wiping..." : "Wipe Data"}
          </button>
        </div>

        <p>Load status: {loadMessage}</p>
        {wipeMessage ? <p>Wipe status: {wipeMessage}</p> : null}
      </section>

      <section className="panel">
        <h2>Run Query</h2>
        <form onSubmit={handleRun}>
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ask a question from loaded wiki content"
            rows={4}
          />
          <div className="row">
            <button type="submit" disabled={!query.trim() || runState === "loading"}>
              {runState === "loading" ? "Running..." : "Run"}
            </button>
            <span className={`symbol state-${runState}`} aria-label="run result symbol">
              {runSymbol(runState)}
            </span>
          </div>
        </form>
      </section>

      <section className="panel">
        <h2>Final Readout</h2>
        <section aria-labelledby="final-readout-main-question">
          <h3 id="final-readout-main-question">Main question</h3>
          <p>{lastRunResponse?.main_question.trim() || submittedQuery || "No query submitted yet."}</p>
        </section>
        <section aria-labelledby="final-readout-final-answer">
          <h3 id="final-readout-final-answer">Final answer</h3>
          <p>{answer || "No answer yet."}</p>
        </section>
        <section aria-labelledby="final-readout-subquestions">
          <h3 id="final-readout-subquestions">Subquestions &amp; subanswers</h3>
          {(lastRunResponse?.sub_qa?.length ?? 0) > 0 ? (
            <div className="subquestions-list">
              {(lastRunResponse?.sub_qa ?? []).map((item, index) => {
                const subAnswer = item.sub_answer.trim();
                const subAgentResponse = item.sub_agent_response?.trim() ?? "";
                const toolCallInput = item.tool_call_input?.trim() ?? "";
                return (
                  <details key={`${item.sub_question}-${index}`} className="subquestion-item">
                    <summary>{item.sub_question.trim() || `Subquestion ${index + 1}`}</summary>
                    <div className="subquestion-content">
                      {subAnswer ? (
                        <p>
                          <strong>Subagent answer:</strong> {subAnswer}
                        </p>
                      ) : null}
                      {subAgentResponse ? (
                        <p>
                          <strong>Subagent response:</strong> {subAgentResponse}
                        </p>
                      ) : null}
                      {toolCallInput ? (
                        <p>
                          <strong>Tool call input:</strong> {toolCallInput}
                        </p>
                      ) : null}
                    </div>
                  </details>
                );
              })}
            </div>
          ) : (
            <p>No subquestions for this run.</p>
          )}
        </section>
      </section>
    </main>
  );
}

function mergeWikiSourcesWithFallback(apiSources: WikiSourceOption[]): WikiSourceOption[] {
  const apiSourcesById = new Map(apiSources.map((source) => [source.source_id, source]));
  const merged = DEFAULT_WIKI_SOURCES.map((fallbackSource) => {
    const apiSource = apiSourcesById.get(fallbackSource.source_id);
    return apiSource ? { ...fallbackSource, ...apiSource } : fallbackSource;
  });
  const extraApiSources = apiSources.filter((source) => !DEFAULT_WIKI_SOURCES.some((item) => item.source_id === source.source_id));
  return merged.concat(extraApiSources);
}
