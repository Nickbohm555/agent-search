import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AgentStageName,
  AgentStageRuntimeStatus,
  RequestState,
  RuntimeAgentRunResponse,
  WikiSourceOption,
  cancelInternalDataLoad,
  getAgentRunStatus,
  getInternalDataLoadStatus,
  listWikiSources,
  startAgentRun,
  startInternalDataLoad,
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
  const orderedStages: AgentStageName[] = ["decompose", "expand", "search", "rerank", "answer", "final"];
  const [wikiSources, setWikiSources] = useState<WikiSourceOption[]>(DEFAULT_WIKI_SOURCES);
  const [wikiSourceId, setWikiSourceId] = useState(DEFAULT_WIKI_SOURCES[0]?.source_id ?? "");
  const [loadState, setLoadState] = useState<RequestState>("idle");
  const [loadMessage, setLoadMessage] = useState("Not started.");
  const [loadJobId, setLoadJobId] = useState<string | null>(null);
  const [loadProgress, setLoadProgress] = useState({ completed: 0, total: 0 });
  const [loadProgressMessage, setLoadProgressMessage] = useState("");
  const [wipeState, setWipeState] = useState<RequestState>("idle");
  const [wipeMessage, setWipeMessage] = useState("");

  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [runState, setRunState] = useState<RequestState>("idle");
  const [runJobId, setRunJobId] = useState<string | null>(null);
  const [runStatusMessage, setRunStatusMessage] = useState("Not started.");
  const [runCurrentStage, setRunCurrentStage] = useState("");
  const [decompositionSubQuestions, setDecompositionSubQuestions] = useState<string[]>([]);
  const [stageStatuses, setStageStatuses] = useState<Record<AgentStageName, AgentStageRuntimeStatus>>({
    decompose: "pending",
    expand: "pending",
    search: "pending",
    rerank: "pending",
    answer: "pending",
    final: "pending",
  });
  const [answer, setAnswer] = useState("");
  const [lastRunResponse, setLastRunResponse] = useState<RuntimeAgentRunResponse | null>(null);

  const selectedWikiSource = useMemo(
    () => wikiSources.find((source) => source.source_id === wikiSourceId) ?? null,
    [wikiSources, wikiSourceId],
  );
  const isLoadAll = selectedWikiSource?.source_id === "all";

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
    setLoadMessage(isLoadAll ? "Loading all wiki sources..." : "Loading wiki source...");
    setLoadProgress({ completed: 0, total: 0 });
    setLoadProgressMessage("Starting...");

    const startResult = await startInternalDataLoad(selectedWikiSource.source_id);
    if (!startResult.ok) {
      setLoadState("error");
      setLoadMessage(startResult.error.message);
      return;
    }

    const jobId = startResult.data.job_id;
    setLoadJobId(jobId);

    const poll = async () => {
      const statusResult = await getInternalDataLoadStatus(jobId);
      if (!statusResult.ok) {
        setLoadState("error");
        setLoadMessage(statusResult.error.message);
        setLoadJobId(null);
        return;
      }
      const status = statusResult.data;
      setLoadProgress({ completed: status.completed, total: status.total });
      setLoadProgressMessage(status.message);

      if (status.status === "success") {
        setLoadState("success");
        if (status.response) {
          setLoadMessage(
            `Loaded ${status.response.documents_loaded} docs (${status.response.chunks_created} chunks).`,
          );
        } else {
          setLoadMessage("Load completed.");
        }
        setLoadJobId(null);
        const refresh = await listWikiSources();
        if (refresh.ok) setWikiSources(mergeWikiSourcesWithFallback(refresh.data.sources));
        return;
      }

      if (status.status === "error") {
        setLoadState("error");
        setLoadMessage(status.error ?? "Load failed.");
        setLoadJobId(null);
        return;
      }

      if (status.status === "cancelled") {
        setLoadState("error");
        setLoadMessage("Load cancelled.");
        setLoadJobId(null);
        return;
      }

      setTimeout(poll, 1000);
    };

    poll();
  }

  async function handleCancelLoad(): Promise<void> {
    if (!loadJobId || loadState !== "loading") return;
    const result = await cancelInternalDataLoad(loadJobId);
    if (!result.ok) {
      setLoadState("error");
      setLoadMessage(result.error.message);
      return;
    }
    setLoadProgressMessage("Cancelling...");
  }

  async function handleLoadAction(): Promise<void> {
    if (loadState === "loading") {
      await handleCancelLoad();
      return;
    }
    await handleLoadWiki();
  }

  async function handleWipe(): Promise<void> {
    if (wipeState === "loading") return;

    setWipeState("loading");
    setWipeMessage("Wiping data...");
    const result = await wipeInternalData();

    if (result.ok) {
      setWipeState("success");
      setWipeMessage(result.data.message);
      setLoadState("idle");
      setLoadMessage("Not started.");
      setLoadJobId(null);
      setLoadProgress({ completed: 0, total: 0 });
      setLoadProgressMessage("");
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
    setRunJobId(null);
    setRunStatusMessage("Submitting run...");
    setRunCurrentStage("");
    setDecompositionSubQuestions([]);
    setStageStatuses({
      decompose: "pending",
      expand: "pending",
      search: "pending",
      rerank: "pending",
      answer: "pending",
      final: "pending",
    });
    setAnswer("");
    setLastRunResponse(null);
    console.info("Async run query requested.", { submittedQuery: submitted });

    const startResult = await startAgentRun(submitted);
    if (!startResult.ok) {
      setRunState("error");
      setRunStatusMessage(startResult.error.message);
      setAnswer(startResult.error.message);
      console.error("Async run query failed to start.", {
        submittedQuery: submitted,
        error: startResult.error.message,
      });
      return;
    }

    const jobId = startResult.data.job_id;
    setRunJobId(jobId);
    setRunStatusMessage("Run started.");
    console.info("Async run started.", { submittedQuery: submitted, jobId, runId: startResult.data.run_id });

    const poll = async () => {
      const statusResult = await getAgentRunStatus(jobId);
      if (!statusResult.ok) {
        setRunState("error");
        setRunStatusMessage(statusResult.error.message);
        setAnswer(statusResult.error.message);
        setRunJobId(null);
        console.error("Async run status polling failed.", {
          submittedQuery: submitted,
          jobId,
          error: statusResult.error.message,
        });
        return;
      }

      const status = statusResult.data;
      setRunCurrentStage(status.stage);
      setDecompositionSubQuestions(status.decomposition_sub_questions);
      setRunStatusMessage(status.message || `Run status: ${status.status}`);
      const nextStatuses = computeStageStatuses(orderedStages, status.stage, status.status);
      setStageStatuses(nextStatuses);
      console.info("Async run stage update.", {
        submittedQuery: submitted,
        jobId,
        backendStage: status.stage,
        backendStatus: status.status,
        decompositionSubQuestionCount: status.decomposition_sub_questions.length,
        stageStatuses: nextStatuses,
      });

      if (status.status === "success") {
        const response = status.result ?? {
          main_question: submitted,
          sub_qa: status.sub_qa,
          output: status.output,
        };
        setRunState("success");
        setLastRunResponse(response);
        setAnswer(response.output);
        setRunStatusMessage(status.message || "Completed.");
        setRunJobId(null);
        console.info("Async run completed.", {
          submittedQuery: submitted,
          jobId,
          hasMainQuestion: Boolean(response.main_question.trim()),
          subQuestionCount: response.sub_qa.length,
          outputLength: response.output.length,
        });
        return;
      }

      if (status.status === "error" || status.status === "cancelled") {
        setRunState("error");
        const failureMessage = status.error || status.message || `Run ${status.status}.`;
        setRunStatusMessage(failureMessage);
        setAnswer(failureMessage);
        setRunJobId(null);
        console.error("Async run finished with non-success status.", {
          submittedQuery: submitted,
          jobId,
          backendStatus: status.status,
          error: status.error,
        });
        return;
      }

      setTimeout(poll, 1000);
    };

    poll();
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
            onClick={handleLoadAction}
            disabled={!selectedWikiSource || selectedWikiSource.already_loaded}
          >
            {loadState === "loading"
              ? "Cancel Load"
              : isLoadAll
                ? "Load All Sources"
                : "Load Wiki Source"}
          </button>
          <button type="button" onClick={handleWipe} disabled={wipeState === "loading"}>
            {wipeState === "loading" ? "Wiping..." : "Wipe Data"}
          </button>
        </div>

        <div className="progress-row">
          <progress
            max={loadProgress.total || 1}
            value={loadProgress.completed}
            aria-label="Load progress"
          />
          <span className="progress-label">
            {loadProgress.total > 0
              ? `${Math.min(100, Math.round((loadProgress.completed / loadProgress.total) * 100))}%`
              : "0%"}
          </span>
        </div>
        {loadProgressMessage ? <p>Progress: {loadProgressMessage}</p> : null}

        <p>Load status: {loadMessage}</p>
        {loadState !== "loading" && wipeMessage ? <p>Wipe status: {wipeMessage}</p> : null}
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
        <p>Run status: {runStatusMessage}</p>
        {runJobId ? <p>Run job id: {runJobId}</p> : null}
      </section>

      <section className="panel stage-rail-panel">
        <h2>Run Timeline</h2>
        <p>
          Current stage: {toDisplayStageName(runCurrentStage) || "Not started"}
        </p>
        <ol className="stage-rail" aria-label="Run stage timeline">
          {orderedStages.map((stage) => (
            <li key={stage} className={`stage-rail-item stage-${stageStatuses[stage]}`}>
              <span className={`stage-dot stage-dot-${stageStatuses[stage]}`} aria-hidden="true" />
              <span className="stage-name">{stage}</span>
              <span className={`stage-status stage-status-${stageStatuses[stage]}`}>{stageStatuses[stage]}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="panel decompose-panel">
        <h2>Decompose</h2>
        <p>Subquestion count: {decompositionSubQuestions.length}</p>
        <div className="decompose-indicators" aria-label="Decompose normalization indicators">
          <span className={`decompose-indicator ${endsWithQuestionMark(decompositionSubQuestions) ? "ok" : "warn"}`}>
            Ends with ?: {endsWithQuestionMark(decompositionSubQuestions) ? "yes" : "no"}
          </span>
          <span className={`decompose-indicator ${hasNoDuplicateQuestions(decompositionSubQuestions) ? "ok" : "warn"}`}>
            Dedupe: {hasNoDuplicateQuestions(decompositionSubQuestions) ? "pass" : "duplicates found"}
          </span>
        </div>
        {decompositionSubQuestions.length > 0 ? (
          <ol className="decompose-question-list" aria-label="Decomposed subquestions">
            {decompositionSubQuestions.map((subQuestion, index) => (
              <li key={`${index}-${subQuestion}`} className="decompose-question-item">
                {subQuestion.trim() || `Subquestion ${index + 1}`}
              </li>
            ))}
          </ol>
        ) : (
          <p>No decomposed subquestions yet.</p>
        )}
      </section>

      <section className="panel final-readout-panel">
        <h2>Final Readout</h2>
        <section className="final-readout-section" aria-labelledby="final-readout-main-question">
          <h3 id="final-readout-main-question">Main question</h3>
          <p className="readout-body">{lastRunResponse?.main_question.trim() || submittedQuery || "No query submitted yet."}</p>
        </section>
        <section className="final-readout-section" aria-labelledby="final-readout-final-answer">
          <h3 id="final-readout-final-answer">Final answer</h3>
          <p className="readout-body">{answer || "No answer yet."}</p>
        </section>
        <section className="final-readout-section" aria-labelledby="final-readout-subquestions">
          <h3 id="final-readout-subquestions">Subquestions &amp; subanswers</h3>
          {(lastRunResponse?.sub_qa?.length ?? 0) > 0 ? (
            <div className="subquestions-list">
              {(lastRunResponse?.sub_qa ?? []).map((item, index) => {
                const subAnswer = item.sub_answer?.trim() ?? "";
                const toolCallInput = item.tool_call_input?.trim() ?? "";
                const summaryId = `subquestion-summary-${index}`;
                const contentId = `subquestion-content-${index}`;
                return (
                  <details key={`${item.sub_question}-${index}`} className="subquestion-item">
                    <summary id={summaryId}>{item.sub_question.trim() || `Subquestion ${index + 1}`}</summary>
                    <div className="subquestion-content" id={contentId} role="region" aria-labelledby={summaryId}>
                      {subAnswer ? (
                        <p className="subquestion-answer">
                          <strong>Answer:</strong> {subAnswer}
                        </p>
                      ) : null}
                      {toolCallInput ? (
                        <p className="subquestion-tool-input">
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

function mapBackendStageToCanonical(stage: string): AgentStageName | null {
  if (stage === "subquestions_ready" || stage === "decompose") return "decompose";
  if (stage === "expand") return "expand";
  if (stage === "search") return "search";
  if (stage === "rerank") return "rerank";
  if (stage === "answer") return "answer";
  if (stage === "synthesize_final" || stage === "final") return "final";
  return null;
}

function computeStageStatuses(
  orderedStages: AgentStageName[],
  backendStage: string,
  backendStatus: string,
): Record<AgentStageName, AgentStageRuntimeStatus> {
  const mappedStage = mapBackendStageToCanonical(backendStage);
  const mappedIndex = mappedStage ? orderedStages.indexOf(mappedStage) : -1;
  const result = orderedStages.reduce<Record<AgentStageName, AgentStageRuntimeStatus>>(
    (acc, stage) => ({ ...acc, [stage]: "pending" }),
    {} as Record<AgentStageName, AgentStageRuntimeStatus>,
  );

  if (mappedIndex < 0) {
    return result;
  }

  for (let index = 0; index < mappedIndex; index += 1) {
    result[orderedStages[index]] = "completed";
  }

  if (backendStatus === "error" || backendStatus === "cancelled") {
    result[orderedStages[mappedIndex]] = "error";
    return result;
  }

  if (backendStatus === "success") {
    result[orderedStages[mappedIndex]] = "completed";
    return result;
  }

  result[orderedStages[mappedIndex]] = "in_progress";
  return result;
}

function toDisplayStageName(stage: string): string {
  const mapped = mapBackendStageToCanonical(stage);
  if (mapped) return mapped;
  if (!stage.trim()) return "";
  return stage;
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

function endsWithQuestionMark(subQuestions: string[]): boolean {
  if (subQuestions.length === 0) return false;
  return subQuestions.every((subQuestion) => subQuestion.trim().endsWith("?"));
}

function hasNoDuplicateQuestions(subQuestions: string[]): boolean {
  if (subQuestions.length === 0) return false;
  const normalized = subQuestions.map((subQuestion) => subQuestion.trim().toLowerCase());
  return normalized.length === new Set(normalized).size;
}
