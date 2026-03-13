import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AgentStageName,
  AgentStageRuntimeStatus,
  RequestState,
  RuntimeLifecycleEvent,
  RuntimeAgentRunResponse,
  RuntimeSubquestionDecision,
  RuntimeSubquestionPausePayload,
  SearchCandidateRow,
  SubQuestionAnswer,
  SubQuestionArtifact,
  WikiSourceOption,
  cancelInternalDataLoad,
  getInternalDataLoadStatus,
  listWikiSources,
  resumeAgentRun,
  startAgentRun,
  startInternalDataLoad,
  subscribeToAgentRunEvents,
  wipeInternalData,
} from "./utils/api";
import { DEFAULT_WIKI_SOURCES } from "./utils/constants";

function runSymbol(state: RequestState): string {
  if (state === "success") return "✓";
  if (state === "error") return "✗";
  if (state === "loading") return "…";
  return "-";
}

function formatLatency(ms: number | null): string {
  if (ms === null) return "n/a";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

type RunSummary = {
  searchRawHitsTotal: number;
  searchDedupedHitsTotal: number;
  rerankRowsTotal: number;
  rerankBypassedCount: number;
  citationCoverageCount: number;
  citationCoverageTotal: number;
  totalLatencyMs: number | null;
};

type SubquestionDecisionDraft = {
  action: RuntimeSubquestionDecision["action"];
  editedText: string;
};

export default function App() {
  const streamErrorGracePeriodMs = 3000;
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
  const [runEvents, setRunEvents] = useState<RuntimeLifecycleEvent[]>([]);
  const [runSummary, setRunSummary] = useState<RunSummary>({
    searchRawHitsTotal: 0,
    searchDedupedHitsTotal: 0,
    rerankRowsTotal: 0,
    rerankBypassedCount: 0,
    citationCoverageCount: 0,
    citationCoverageTotal: 0,
    totalLatencyMs: null,
  });
  const [decompositionSubQuestions, setDecompositionSubQuestions] = useState<string[]>([]);
  const [subQuestionArtifacts, setSubQuestionArtifacts] = useState<SubQuestionArtifact[]>([]);
  const [runSubQa, setRunSubQa] = useState<SubQuestionAnswer[]>([]);
  const [stageStatuses, setStageStatuses] = useState<Record<AgentStageName, AgentStageRuntimeStatus>>({
    decompose: "pending",
    expand: "pending",
    search: "pending",
    rerank: "pending",
    answer: "pending",
    final: "pending",
  });
  const [lastSuccessfulSynthesis, setLastSuccessfulSynthesis] = useState<RuntimeAgentRunResponse | null>(null);
  const [pausedPayload, setPausedPayload] = useState<RuntimeSubquestionPausePayload | null>(null);
  const [reviewDrafts, setReviewDrafts] = useState<Record<string, SubquestionDecisionDraft>>({});
  const [resumeState, setResumeState] = useState<RequestState>("idle");
  const [resumeMessage, setResumeMessage] = useState("");
  const runEventsUnsubscribeRef = useRef<(() => void) | null>(null);
  const runStreamRef = useRef<{ jobId: string | null; terminal: boolean }>({ jobId: null, terminal: false });
  const runStreamErrorTimeoutRef = useRef<number | null>(null);

  const selectedWikiSource = useMemo(
    () => wikiSources.find((source) => source.source_id === wikiSourceId) ?? null,
    [wikiSources, wikiSourceId],
  );
  const isLoadAll = selectedWikiSource?.source_id === "all";
  const finalCitationMap = useMemo(
    () => buildFinalCitationMap(lastSuccessfulSynthesis?.final_citations ?? []),
    [lastSuccessfulSynthesis],
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

  useEffect(() => {
    return () => {
      if (runStreamErrorTimeoutRef.current !== null) {
        window.clearTimeout(runStreamErrorTimeoutRef.current);
        runStreamErrorTimeoutRef.current = null;
      }
      runEventsUnsubscribeRef.current?.();
      runEventsUnsubscribeRef.current = null;
      runStreamRef.current = { jobId: null, terminal: false };
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
    setRunEvents([]);
    setDecompositionSubQuestions([]);
    setSubQuestionArtifacts([]);
    setRunSubQa([]);
    setPausedPayload(null);
    setReviewDrafts({});
    setResumeState("idle");
    setResumeMessage("");
    setRunSummary({
      searchRawHitsTotal: 0,
      searchDedupedHitsTotal: 0,
      rerankRowsTotal: 0,
      rerankBypassedCount: 0,
      citationCoverageCount: 0,
      citationCoverageTotal: 0,
      totalLatencyMs: null,
    });
    setStageStatuses({
      decompose: "pending",
      expand: "pending",
      search: "pending",
      rerank: "pending",
      answer: "pending",
      final: "pending",
    });
    console.info("Async run query requested.", { submittedQuery: submitted });

    const startResult = await startAgentRun(submitted);
    if (!startResult.ok) {
      setRunState("error");
      setRunStatusMessage(startResult.error.message);
      console.error("Async run query failed to start.", {
        submittedQuery: submitted,
        error: startResult.error.message,
      });
      return;
    }

    const jobId = startResult.data.job_id;
    setRunJobId(jobId);
    setRunStatusMessage("Run started.");
    if (runStreamErrorTimeoutRef.current !== null) {
      window.clearTimeout(runStreamErrorTimeoutRef.current);
      runStreamErrorTimeoutRef.current = null;
    }
    runStreamRef.current = { jobId, terminal: false };
    console.info("Async run started.", { submittedQuery: submitted, jobId, runId: startResult.data.run_id });
    openRunEventStream(jobId, submitted);
  }

  function openRunEventStream(jobId: string, submittedQueryValue: string): void {
    runEventsUnsubscribeRef.current?.();
    runEventsUnsubscribeRef.current = subscribeToAgentRunEvents(jobId, {
      onEvent: (lifecycleEvent) => {
        if (runStreamErrorTimeoutRef.current !== null) {
          window.clearTimeout(runStreamErrorTimeoutRef.current);
          runStreamErrorTimeoutRef.current = null;
        }
        setRunEvents((current) => current.concat(lifecycleEvent));
        setRunCurrentStage(lifecycleEvent.stage);
        setRunStatusMessage(formatLifecycleEventLabel(lifecycleEvent));
        setStageStatuses((current) => computeStageStatusesFromEvents(orderedStages, current, lifecycleEvent));
        applyRunEventData({
          lifecycleEvent,
          submittedQuery: submittedQueryValue,
          jobId,
          setDecompositionSubQuestions,
          setSubQuestionArtifacts,
          setRunSubQa,
          setRunSummary,
          setLastSuccessfulSynthesis,
        });
        console.info("Async run lifecycle event received.", {
          submittedQuery: submittedQueryValue,
          jobId,
          eventType: lifecycleEvent.event_type,
          backendStage: lifecycleEvent.stage,
          backendStatus: lifecycleEvent.status,
        });

        if (lifecycleEvent.event_type === "run.paused" && lifecycleEvent.interrupt_payload) {
          setRunState("loading");
          setRunStatusMessage("Run paused for subquestion review.");
          setPausedPayload(lifecycleEvent.interrupt_payload);
          setReviewDrafts(buildInitialReviewDrafts(lifecycleEvent.interrupt_payload));
          setResumeState("idle");
          setResumeMessage("");
          runEventsUnsubscribeRef.current?.();
          runEventsUnsubscribeRef.current = null;
          return;
        }

        if (isTerminalLifecycleEvent(lifecycleEvent)) {
          runStreamRef.current = { jobId, terminal: true };
          setRunState(lifecycleEvent.status === "success" ? "success" : "error");
          setPausedPayload(null);
          setReviewDrafts({});
          setResumeState("idle");
          setResumeMessage("");
          if (lifecycleEvent.status !== "success") {
            setRunStatusMessage(lifecycleEvent.error || formatLifecycleEventLabel(lifecycleEvent));
          }
          setRunJobId(null);
          runEventsUnsubscribeRef.current?.();
          runEventsUnsubscribeRef.current = null;
        }
      },
      onError: () => {
        if (runStreamRef.current.jobId !== jobId || runStreamRef.current.terminal) {
          return;
        }
        if (runStreamErrorTimeoutRef.current !== null) {
          window.clearTimeout(runStreamErrorTimeoutRef.current);
        }
        runStreamErrorTimeoutRef.current = window.setTimeout(() => {
          if (runStreamRef.current.jobId !== jobId || runStreamRef.current.terminal) {
            return;
          }
          setRunState("error");
          setRunStatusMessage("Run event stream disconnected.");
          setRunJobId(null);
          runStreamRef.current = { jobId, terminal: true };
          runEventsUnsubscribeRef.current?.();
          runEventsUnsubscribeRef.current = null;
          console.error("Async run event stream failed.", { submittedQuery: submittedQueryValue, jobId });
        }, streamErrorGracePeriodMs);
      },
    });
  }

  function handleDecisionActionChange(subquestionId: string, action: RuntimeSubquestionDecision["action"]): void {
    setReviewDrafts((current) => ({
      ...current,
      [subquestionId]: {
        ...(current[subquestionId] ?? { action: "approve", editedText: "" }),
        action,
      },
    }));
  }

  function handleDecisionEditTextChange(subquestionId: string, editedText: string): void {
    setReviewDrafts((current) => ({
      ...current,
      [subquestionId]: {
        ...(current[subquestionId] ?? { action: "edit", editedText: "" }),
        editedText,
      },
    }));
  }

  async function handleResumeRun(skipReview = false): Promise<void> {
    if (!runJobId || !pausedPayload || resumeState === "loading") return;

    const decisions = skipReview
      ? pausedPayload.subquestions.map((item) => ({ subquestion_id: item.subquestion_id, action: "skip" as const }))
      : buildResumeDecisions(pausedPayload, reviewDrafts);

    if (decisions === null) {
      setResumeState("error");
      setResumeMessage("Each edited subquestion needs replacement text before resuming.");
      return;
    }

    setResumeState("loading");
    setResumeMessage(skipReview ? "Skipping review and resuming..." : "Submitting review decisions...");
    const resumeResult = await resumeAgentRun(runJobId, {
      checkpoint_id: pausedPayload.checkpoint_id,
      decisions,
    });

    if (!resumeResult.ok) {
      setResumeState("error");
      setResumeMessage(resumeResult.error.message);
      return;
    }

    setPausedPayload(null);
    setReviewDrafts({});
    setResumeState("success");
    setResumeMessage("Resume accepted.");
    setRunState("loading");
    setRunStatusMessage(resumeResult.data.message);
    setRunCurrentStage(resumeResult.data.stage);
    runStreamRef.current = { jobId: runJobId, terminal: false };
    openRunEventStream(runJobId, submittedQuery);
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

      {pausedPayload ? (
        <section className="panel paused-review-panel" aria-labelledby="paused-review-title">
          <h2 id="paused-review-title">Subquestion Review</h2>
          <p>
            Review checkpoint <strong>{pausedPayload.checkpoint_id}</strong> and choose how each proposed subquestion
            should continue.
          </p>
          <ol className="paused-review-list" aria-label="Paused subquestion review list">
            {pausedPayload.subquestions.map((subquestion, index) => {
              const draft = reviewDrafts[subquestion.subquestion_id] ?? {
                action: "approve" as const,
                editedText: subquestion.sub_question,
              };
              const fieldId = `subquestion-review-${subquestion.subquestion_id}`;
              return (
                <li key={subquestion.subquestion_id} className="paused-review-item">
                  <p className="paused-review-title">
                    <strong>Subquestion {index + 1}:</strong> {subquestion.sub_question}
                  </p>
                  <label htmlFor={`${fieldId}-action`}>Decision</label>
                  <select
                    id={`${fieldId}-action`}
                    value={draft.action}
                    onChange={(event) =>
                      handleDecisionActionChange(
                        subquestion.subquestion_id,
                        event.target.value as RuntimeSubquestionDecision["action"],
                      )
                    }
                    disabled={resumeState === "loading"}
                  >
                    <option value="approve">Approve</option>
                    <option value="edit">Edit</option>
                    <option value="deny">Deny</option>
                    <option value="skip">Skip</option>
                  </select>
                  {draft.action === "edit" ? (
                    <>
                      <label htmlFor={`${fieldId}-edited-text`}>Edited text</label>
                      <input
                        id={`${fieldId}-edited-text`}
                        type="text"
                        value={draft.editedText}
                        onChange={(event) => handleDecisionEditTextChange(subquestion.subquestion_id, event.target.value)}
                        placeholder="Rewrite this subquestion"
                        disabled={resumeState === "loading"}
                      />
                    </>
                  ) : null}
                </li>
              );
            })}
          </ol>
          <div className="row">
            <button type="button" onClick={() => void handleResumeRun(false)} disabled={resumeState === "loading"}>
              {resumeState === "loading" ? "Submitting..." : "Resume Run"}
            </button>
            <button type="button" onClick={() => void handleResumeRun(true)} disabled={resumeState === "loading"}>
              Skip Review
            </button>
          </div>
          {resumeMessage ? <p>Resume status: {resumeMessage}</p> : null}
        </section>
      ) : null}

      <section className="panel run-summary-panel">
        <h2>Run Summary</h2>
        <div className="summary-grid">
          <div className="summary-item">
            <span className="summary-label">Total latency</span>
            <span className="summary-value">{formatLatency(runSummary.totalLatencyMs)}</span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Search hits</span>
            <span className="summary-value">
              {runSummary.searchDedupedHitsTotal}/{runSummary.searchRawHitsTotal} deduped
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Rerank rows</span>
            <span className="summary-value">
              {runSummary.rerankRowsTotal} (bypassed: {runSummary.rerankBypassedCount})
            </span>
          </div>
          <div className="summary-item">
            <span className="summary-label">Citation coverage</span>
            <span className="summary-value">
              {runSummary.citationCoverageCount}/{runSummary.citationCoverageTotal}
            </span>
          </div>
        </div>
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

      <section className="panel lifecycle-events-panel">
        <h2>Streamed Events</h2>
        {runEvents.length > 0 ? (
          <ol className="lifecycle-event-list" aria-label="Streamed lifecycle events">
            {runEvents.map((eventItem) => (
              <li key={eventItem.event_id} className="lifecycle-event-item">
                <strong>{eventItem.event_type}</strong>
                {" · "}
                {eventItem.stage}
                {" · "}
                {eventItem.status}
                {eventItem.error ? ` · ${eventItem.error}` : ""}
              </li>
            ))}
          </ol>
        ) : (
          <p>No streamed events yet.</p>
        )}
      </section>

      <section className="panel decompose-panel">
        <details open>
          <summary className="panel-summary">
            <h2>Decompose</h2>
          </summary>
          <div className="panel-body">
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
          </div>
        </details>
      </section>

      <section className="panel expand-panel">
        <details open>
          <summary className="panel-summary">
            <h2>Expand</h2>
          </summary>
          <div className="panel-body">
            {decompositionSubQuestions.length > 0 ? (
              <ol className="expand-lane-list" aria-label="Expanded query groups">
                {decompositionSubQuestions.map((subQuestion, index) => {
                  const artifact = subQuestionArtifacts[index] ?? subQuestionArtifacts.find((item) => item.sub_question === subQuestion);
                  const expandedQueries = artifact?.expanded_queries ?? [];
                  const fallbackToOriginalOnly = isExpansionFallback({
                    subQuestion,
                    expandedQueries,
                  });
                  return (
                    <li key={`${index}-${subQuestion}`} className="expand-lane-item">
                      <p className="expand-lane-title">
                        <strong>Subquestion {index + 1}:</strong> {subQuestion}
                      </p>
                      <p className="expand-original-question">
                        <strong>Original:</strong> {subQuestion}
                      </p>
                      {expandedQueries.length > 0 ? (
                        <ol className="expand-query-list" aria-label={`Expanded queries for subquestion ${index + 1}`}>
                          {expandedQueries.map((queryItem, queryIndex) => (
                            <li key={`${index}-${queryIndex}-${queryItem}`} className="expand-query-item">
                              {queryItem}
                            </li>
                          ))}
                        </ol>
                      ) : (
                        <p>No expanded queries yet.</p>
                      )}
                      {fallbackToOriginalOnly ? <span className="expansion-fallback-badge">Fallback: original only</span> : null}
                    </li>
                  );
                })}
              </ol>
            ) : (
              <p>No expansion data yet.</p>
            )}
          </div>
        </details>
      </section>

      <section className="panel search-panel">
        <details open>
          <summary className="panel-summary">
            <h2>Search</h2>
          </summary>
          <div className="panel-body">
            {decompositionSubQuestions.length > 0 ? (
              <ol className="search-lane-list" aria-label="Search candidate groups">
                {decompositionSubQuestions.map((subQuestion, index) => {
                  const artifact =
                    subQuestionArtifacts[index] ?? subQuestionArtifacts.find((item) => item.sub_question === subQuestion);
                  const mergeStats = getSearchMergeStats(artifact);
                  const previewRows = getSearchPreviewRows(artifact, 3);
                  return (
                    <li key={`${index}-${subQuestion}`} className="search-lane-item">
                      <p className="search-lane-title">
                        <strong>Subquestion {index + 1}:</strong> {subQuestion}
                      </p>
                      <p className="search-candidate-count">Merged candidates: {mergeStats.dedupedHits}</p>
                      <div className="search-merge-stats" aria-label={`Search merge stats for subquestion ${index + 1}`}>
                        <span className="search-merge-stat">Raw hits: {mergeStats.rawHits}</span>
                        <span className="search-merge-stat">Deduped hits: {mergeStats.dedupedHits}</span>
                      </div>
                      {previewRows.length > 0 ? (
                        <ol className="search-preview-list" aria-label={`Search preview rows for subquestion ${index + 1}`}>
                          {previewRows.map((row) => (
                            <li key={`${index}-${row.citation_index}-${row.document_id}`} className="search-preview-item">
                              <p className="search-preview-title">
                                <strong>{row.title || "Untitled source"}</strong>
                              </p>
                              <p className="search-preview-source">
                                <strong>Source:</strong> {row.source || "unknown"}
                              </p>
                              <p className="search-preview-snippet">{toSnippet(row.content)}</p>
                            </li>
                          ))}
                        </ol>
                      ) : (
                        <p>No retrieved candidates yet.</p>
                      )}
                    </li>
                  );
                })}
              </ol>
            ) : (
              <p>No search data yet.</p>
            )}
          </div>
        </details>
      </section>

      <section className="panel rerank-panel">
        <details open>
          <summary className="panel-summary">
            <h2>Rerank</h2>
          </summary>
          <div className="panel-body">
            {decompositionSubQuestions.length > 0 ? (
              <ol className="rerank-lane-list" aria-label="Reranked evidence groups">
                {decompositionSubQuestions.map((subQuestion, index) => {
                  const artifact =
                    subQuestionArtifacts[index] ?? subQuestionArtifacts.find((item) => item.sub_question === subQuestion);
                  const rerankRows = getRerankRows(artifact);
                  const matchingSubQa = runSubQa.find((item) => item.sub_question === subQuestion);
                  const fallbackBypassed = isRerankFallback({
                    artifact,
                    subQa: matchingSubQa,
                  });
                  const orderChanged = didRerankOrderChange(artifact);
                  return (
                    <li key={`${index}-${subQuestion}`} className="rerank-lane-item">
                      <p className="rerank-lane-title">
                        <strong>Subquestion {index + 1}:</strong> {subQuestion}
                      </p>
                      <p className="rerank-order-change">
                        <strong>Order changed:</strong> {orderChanged ? "yes" : "no"}
                      </p>
                      {fallbackBypassed ? <span className="rerank-fallback-badge">Fallback: reranking bypassed</span> : null}
                      {rerankRows.length > 0 ? (
                        <ol className="rerank-row-list" aria-label={`Reranked evidence rows for subquestion ${index + 1}`}>
                          {rerankRows.map((row) => (
                            <li
                              key={`${index}-${row.citation_index}-${row.document_id}`}
                              className="rerank-row-item"
                              id={toRerankEvidenceRowId(index, row.citation_index)}
                            >
                              <p className="rerank-row-title">
                                <strong>
                                  [{row.citation_index}] {row.title || "Untitled source"}
                                </strong>
                              </p>
                              <p className="rerank-row-meta">
                                <strong>Rank:</strong> {row.rank}
                                {" · "}
                                <strong>Score:</strong> {row.score === null || row.score === undefined ? "n/a" : row.score}
                              </p>
                              <p className="rerank-row-source">
                                <strong>Source:</strong> {row.source || "unknown"}
                              </p>
                              <p className="rerank-row-snippet">{toSnippet(row.content)}</p>
                            </li>
                          ))}
                        </ol>
                      ) : (
                        <p>No reranked evidence yet.</p>
                      )}
                    </li>
                  );
                })}
              </ol>
            ) : (
              <p>No rerank data yet.</p>
            )}
          </div>
        </details>
      </section>

      <section className="panel subanswer-panel">
        <details open>
          <summary className="panel-summary">
            <h2>Subanswer</h2>
          </summary>
          <div className="panel-body">
            {decompositionSubQuestions.length > 0 ? (
              <ol className="subanswer-lane-list" aria-label="Subanswer groups">
                {decompositionSubQuestions.map((subQuestion, index) => {
                  const subQa = runSubQa[index] ?? runSubQa.find((item) => item.sub_question === subQuestion);
                  const subAnswer = subQa?.sub_answer?.trim() ?? "";
                  const citationIndices = subQa?.sub_answer_citations ?? extractCitationIndices(subAnswer);
                  const fallback = subQa?.sub_answer_is_fallback ?? isFallbackSubanswer(subAnswer);
                  return (
                    <li key={`${index}-${subQuestion}`} className="subanswer-lane-item">
                      <p className="subanswer-lane-title">
                        <strong>Subquestion {index + 1}:</strong> {subQuestion}
                      </p>
                      {subAnswer ? (
                        <p className="subanswer-body">
                          <strong>Answer:</strong> {subAnswer}
                        </p>
                      ) : (
                        <p>No subanswer yet.</p>
                      )}
                      {fallback ? <span className="subanswer-fallback-badge">Fallback: nothing relevant found</span> : null}
                      {citationIndices.length > 0 ? (
                        <p className="subanswer-citations">
                          <strong>Citations:</strong>{" "}
                          {citationIndices.map((citationIndex) => (
                            <a
                              key={`${index}-${citationIndex}`}
                              className="subanswer-citation-link"
                              href={`#${toRerankEvidenceRowId(index, citationIndex)}`}
                            >
                              [{citationIndex}]
                            </a>
                          ))}
                        </p>
                      ) : null}
                    </li>
                  );
                })}
              </ol>
            ) : (
              <p>No subanswers yet.</p>
            )}
          </div>
        </details>
      </section>

      <section className="panel final-readout-panel">
        <h2>Final Synthesis</h2>
        {runState === "loading" && lastSuccessfulSynthesis ? (
          <p className="final-synthesis-preserved">Showing previous successful synthesis while current run is in progress.</p>
        ) : null}
        <section className="final-readout-section" aria-labelledby="final-readout-main-question">
          <h3 id="final-readout-main-question">Main question</h3>
          <p className="readout-body">{lastSuccessfulSynthesis?.main_question.trim() || "No synthesized run yet."}</p>
        </section>
        <section className="final-readout-section" aria-labelledby="final-readout-final-answer">
          <h3 id="final-readout-final-answer">Final answer</h3>
          <p className="readout-body">
            {renderAnswerWithCitations(
              lastSuccessfulSynthesis?.output.trim() || "No synthesized answer yet.",
              finalCitationMap,
            )}
          </p>
        </section>
        <section className="final-readout-section" aria-labelledby="final-readout-citations">
          <h3 id="final-readout-citations">Citations</h3>
          {lastSuccessfulSynthesis && lastSuccessfulSynthesis.final_citations.length > 0 ? (
            <ol className="final-citation-list">
              {lastSuccessfulSynthesis.final_citations.map((citation) => (
                <li key={`final-citation-${citation.citation_index}`} className="final-citation-item">
                  <p className="final-citation-title">
                    <strong>[{citation.citation_index}]</strong> {citation.title || "Untitled source"}
                  </p>
                  <p className="final-citation-source">
                    <strong>Source:</strong>{" "}
                    {isHttpUrl(citation.source) ? (
                      <a href={citation.source} target="_blank" rel="noreferrer">
                        {citation.source}
                      </a>
                    ) : (
                      citation.source || "unknown"
                    )}
                  </p>
                  <p className="final-citation-snippet">{toSnippet(citation.content)}</p>
                </li>
              ))}
            </ol>
          ) : (
            <p>No citations yet.</p>
          )}
        </section>
        <section className="final-readout-section" aria-labelledby="final-readout-summary">
          <h3 id="final-readout-summary">Supporting summary</h3>
          {lastSuccessfulSynthesis ? (
            <div className="final-synthesis-summary">
              <p>
                Subanswers used: {countNonEmptySubanswers(lastSuccessfulSynthesis.sub_qa)}/{lastSuccessfulSynthesis.sub_qa.length}
              </p>
              <p>
                Citation coverage: {countSubanswersWithCitations(lastSuccessfulSynthesis.sub_qa)}/{lastSuccessfulSynthesis.sub_qa.length} subanswers with citations ({countTotalCitations(lastSuccessfulSynthesis.sub_qa)} total citations)
              </p>
              <p>
                Fallback subanswers: {countFallbackSubanswers(lastSuccessfulSynthesis.sub_qa)}
              </p>
            </div>
          ) : (
            <p>No synthesis summary yet.</p>
          )}
        </section>
        <section className="final-readout-section" aria-labelledby="final-readout-subquestions">
          <h3 id="final-readout-subquestions">Subquestions &amp; subanswers</h3>
          {lastSuccessfulSynthesis && lastSuccessfulSynthesis.sub_qa.length > 0 ? (
            <div className="subquestions-list">
              {lastSuccessfulSynthesis.sub_qa.map((item, index) => {
                const subAnswer = item.sub_answer?.trim() ?? "";
                const toolCallInput = item.tool_call_input?.trim() ?? "";
                const citationIndices = getSubanswerCitationIndices(item);
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
                      {citationIndices.length > 0 ? (
                        <p className="subquestion-citation-coverage">
                          <strong>Citation coverage:</strong> {citationIndices.map((citationIndex) => `[${citationIndex}]`).join(" ")}
                        </p>
                      ) : (
                        <p className="subquestion-citation-coverage">
                          <strong>Citation coverage:</strong> none
                        </p>
                      )}
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

function isTerminalLifecycleEvent(event: RuntimeLifecycleEvent): boolean {
  return event.event_type === "run.completed" || event.event_type === "run.failed";
}

function formatLifecycleEventLabel(event: RuntimeLifecycleEvent): string {
  const parts = [event.event_type, event.stage, event.status];
  if (event.error?.trim()) {
    parts.push(event.error.trim());
  }
  return parts.join(" · ");
}

function computeStageStatusesFromEvents(
  orderedStages: AgentStageName[],
  current: Record<AgentStageName, AgentStageRuntimeStatus>,
  event: RuntimeLifecycleEvent,
): Record<AgentStageName, AgentStageRuntimeStatus> {
  const next = { ...current };
  const mappedStage = mapBackendStageToCanonical(event.stage);
  if (!mappedStage) {
    return next;
  }

  if (event.event_type === "stage.started" || event.event_type === "stage.updated" || event.event_type === "stage.retrying") {
    markPreviousStagesCompleted(next, orderedStages, mappedStage);
    next[mappedStage] = "in_progress";
    return next;
  }

  if (event.event_type === "stage.completed") {
    markPreviousStagesCompleted(next, orderedStages, mappedStage);
    next[mappedStage] = "completed";
    return next;
  }

  if (event.event_type === "stage.failed") {
    markPreviousStagesCompleted(next, orderedStages, mappedStage);
    next[mappedStage] = "error";
    return next;
  }

  if (event.event_type === "run.completed") {
    markPreviousStagesCompleted(next, orderedStages, mappedStage);
    next[mappedStage] = "completed";
    return next;
  }

  if (event.event_type === "run.failed") {
    markPreviousStagesCompleted(next, orderedStages, mappedStage);
    next[mappedStage] = "error";
    return next;
  }

  if (event.event_type === "run.paused") {
    markPreviousStagesCompleted(next, orderedStages, mappedStage);
    next[mappedStage] = "completed";
  }

  for (let index = 0; index < orderedStages.length; index += 1) {
    if (orderedStages[index] === mappedStage && next[mappedStage] === "pending" && event.status === "running") {
      next[mappedStage] = "in_progress";
      break;
    }
  }

  return next;
}

function buildInitialReviewDrafts(
  pausedPayload: RuntimeSubquestionPausePayload,
): Record<string, SubquestionDecisionDraft> {
  return Object.fromEntries(
    pausedPayload.subquestions.map((item) => [
      item.subquestion_id,
      {
        action: "approve",
        editedText: item.sub_question,
      },
    ]),
  );
}

function buildResumeDecisions(
  pausedPayload: RuntimeSubquestionPausePayload,
  reviewDrafts: Record<string, SubquestionDecisionDraft>,
): RuntimeSubquestionDecision[] | null {
  const decisions: RuntimeSubquestionDecision[] = [];
  for (const item of pausedPayload.subquestions) {
    const draft = reviewDrafts[item.subquestion_id] ?? { action: "approve", editedText: item.sub_question };
    if (draft.action === "edit") {
      const editedText = draft.editedText.trim();
      if (!editedText) {
        return null;
      }
      decisions.push({
        subquestion_id: item.subquestion_id,
        action: "edit",
        edited_text: editedText,
      });
      continue;
    }

    decisions.push({
      subquestion_id: item.subquestion_id,
      action: draft.action,
    });
  }

  return decisions;
}

function markPreviousStagesCompleted(
  stageStatuses: Record<AgentStageName, AgentStageRuntimeStatus>,
  orderedStages: AgentStageName[],
  activeStage: AgentStageName,
): void {
  const activeIndex = orderedStages.indexOf(activeStage);
  if (activeIndex <= 0) return;
  for (let index = 0; index < activeIndex; index += 1) {
    if (stageStatuses[orderedStages[index]] === "pending") {
      stageStatuses[orderedStages[index]] = "completed";
    }
  }
}

function applyRunEventData(args: {
  lifecycleEvent: RuntimeLifecycleEvent;
  submittedQuery: string;
  jobId: string;
  setDecompositionSubQuestions: (value: string[]) => void;
  setSubQuestionArtifacts: (value: SubQuestionArtifact[]) => void;
  setRunSubQa: (value: SubQuestionAnswer[]) => void;
  setRunSummary: (value: RunSummary) => void;
  setLastSuccessfulSynthesis: (value: RuntimeAgentRunResponse | null) => void;
}): void {
  const {
    lifecycleEvent,
    submittedQuery,
    jobId,
    setDecompositionSubQuestions,
    setSubQuestionArtifacts,
    setRunSubQa,
    setRunSummary,
    setLastSuccessfulSynthesis,
  } = args;

  if (lifecycleEvent.decomposition_sub_questions) {
    setDecompositionSubQuestions(lifecycleEvent.decomposition_sub_questions);
  }
  if (lifecycleEvent.sub_question_artifacts) {
    setSubQuestionArtifacts(lifecycleEvent.sub_question_artifacts);
  }
  if (lifecycleEvent.sub_qa) {
    setRunSubQa(lifecycleEvent.sub_qa);
  }

  if (!lifecycleEvent.sub_question_artifacts || !lifecycleEvent.sub_qa) {
    if (lifecycleEvent.result && mapBackendStageToCanonical(lifecycleEvent.stage) === "final") {
      setLastSuccessfulSynthesis(lifecycleEvent.result);
      setRunSubQa(lifecycleEvent.result.sub_qa);
    }
    return;
  }

  const searchRawHitsTotal = lifecycleEvent.sub_question_artifacts.reduce(
    (sum, artifact) => sum + artifact.retrieval_provenance.length,
    0,
  );
  const searchDedupedHitsTotal = lifecycleEvent.sub_question_artifacts.reduce(
    (sum, artifact) => sum + artifact.retrieved_docs.length,
    0,
  );
  const rerankRowsTotal = lifecycleEvent.sub_question_artifacts.reduce(
    (sum, artifact) => sum + artifact.reranked_docs.length,
    0,
  );
  const rerankBypassedCount = lifecycleEvent.sub_question_artifacts.reduce((sum, artifact) => {
    const matchingSubQa = lifecycleEvent.sub_qa?.find((item) => item.sub_question === artifact.sub_question);
    return sum + (isRerankFallback({ artifact, subQa: matchingSubQa }) ? 1 : 0);
  }, 0);

  setRunSummary({
    searchRawHitsTotal,
    searchDedupedHitsTotal,
    rerankRowsTotal,
    rerankBypassedCount,
    citationCoverageCount: countSubanswersWithCitations(lifecycleEvent.sub_qa),
    citationCoverageTotal: lifecycleEvent.sub_qa.length,
    totalLatencyMs: lifecycleEvent.elapsed_ms ?? null,
  });

  if (lifecycleEvent.event_type === "run.completed") {
    const response = lifecycleEvent.result ?? {
      main_question: submittedQuery,
      sub_qa: lifecycleEvent.sub_qa,
      output: lifecycleEvent.output ?? "",
      final_citations: [],
    };
    const completedStage = mapBackendStageToCanonical(lifecycleEvent.stage);
    if (completedStage === "final") {
      setLastSuccessfulSynthesis(response);
      console.info("Final synthesis panel updated from completed run.", {
        submittedQuery,
        jobId,
        mainQuestion: response.main_question,
        subQuestionCount: response.sub_qa.length,
        citationCoverageCount: countSubanswersWithCitations(response.sub_qa),
      });
    } else {
      console.warn("Run marked as success before synthesis stage completed; preserving previous final synthesis panel.", {
        submittedQuery,
        jobId,
        backendStage: lifecycleEvent.stage,
      });
    }
    setRunSubQa(response.sub_qa);
    console.info("Async run completed.", {
      submittedQuery,
      jobId,
      hasMainQuestion: Boolean(response.main_question.trim()),
      subQuestionCount: response.sub_qa.length,
      outputLength: response.output.length,
    });
  }
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

function isExpansionFallback(args: { subQuestion: string; expandedQueries: string[] }): boolean {
  const normalizedSubQuestion = args.subQuestion.trim().toLowerCase();
  if (!normalizedSubQuestion) return false;
  const normalizedQueries = args.expandedQueries
    .map((item) => item.trim().toLowerCase())
    .filter((item) => item.length > 0);
  if (normalizedQueries.length !== 1) return false;
  return normalizedQueries[0] === normalizedSubQuestion;
}

function getSearchMergeStats(
  artifact: SubQuestionArtifact | undefined,
): { rawHits: number; dedupedHits: number } {
  if (!artifact) {
    return { rawHits: 0, dedupedHits: 0 };
  }
  return {
    rawHits: artifact.retrieval_provenance.length,
    dedupedHits: artifact.retrieved_docs.length,
  };
}

function getSearchPreviewRows(artifact: SubQuestionArtifact | undefined, limit: number): SearchCandidateRow[] {
  if (!artifact || limit <= 0) return [];
  return artifact.retrieved_docs.slice(0, limit);
}

function getRerankRows(artifact: SubQuestionArtifact | undefined): SearchCandidateRow[] {
  if (!artifact) return [];
  return artifact.reranked_docs;
}

function isRerankFallback(args: { artifact: SubQuestionArtifact | undefined; subQa: SubQuestionAnswer | undefined }): boolean {
  if (!args.artifact) return false;
  if (args.subQa?.rerank_bypassed !== undefined) return args.subQa.rerank_bypassed;
  if (args.artifact.reranked_docs.length === 0) return false;
  return args.artifact.reranked_docs.every((item) => item.score === null || item.score === undefined);
}

function didRerankOrderChange(artifact: SubQuestionArtifact | undefined): boolean {
  if (!artifact || artifact.reranked_docs.length === 0 || artifact.retrieved_docs.length === 0) return false;
  const baselineIds = artifact.retrieved_docs.slice(0, artifact.reranked_docs.length).map((item) => item.document_id);
  const rerankedIds = artifact.reranked_docs.map((item) => item.document_id);
  if (baselineIds.length !== rerankedIds.length) return true;
  return baselineIds.some((item, index) => item !== rerankedIds[index]);
}

function toSnippet(content: string): string {
  const normalized = content.trim().replace(/\s+/g, " ");
  if (!normalized) return "No snippet available.";
  if (normalized.length <= 180) return normalized;
  return `${normalized.slice(0, 177)}...`;
}

function isHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

function buildFinalCitationMap(citations: SearchCandidateRow[]): Map<number, SearchCandidateRow> {
  const map = new Map<number, SearchCandidateRow>();
  citations.forEach((item) => {
    map.set(item.citation_index, item);
  });
  return map;
}

function renderAnswerWithCitations(
  text: string,
  citationMap: Map<number, SearchCandidateRow>,
): Array<string | JSX.Element> {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, index) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (!match) return part;
    const citationIndex = Number(match[1]);
    const citation = citationMap.get(citationIndex);
    if (citation && isHttpUrl(citation.source)) {
      return (
        <a
          key={`citation-link-${citationIndex}-${index}`}
          className="inline-citation-link"
          href={citation.source}
          target="_blank"
          rel="noreferrer"
        >
          [{citationIndex}]
        </a>
      );
    }
    return (
      <span key={`citation-text-${citationIndex}-${index}`} className="inline-citation">
        [{citationIndex}]
      </span>
    );
  });
}

function extractCitationIndices(text: string): number[] {
  const values = Array.from(text.matchAll(/\[(\d+)\]/g), (match) => Number(match[1])).filter(
    (item) => Number.isInteger(item) && item > 0,
  );
  return Array.from(new Set(values));
}

function isFallbackSubanswer(subAnswer: string): boolean {
  return subAnswer.trim().toLowerCase() === "nothing relevant found";
}

function toRerankEvidenceRowId(laneIndex: number, citationIndex: number): string {
  return `rerank-evidence-lane-${laneIndex + 1}-citation-${citationIndex}`;
}

function getSubanswerCitationIndices(subQa: SubQuestionAnswer): number[] {
  return subQa.sub_answer_citations ?? extractCitationIndices(subQa.sub_answer ?? "");
}

function countNonEmptySubanswers(subQa: SubQuestionAnswer[]): number {
  return subQa.reduce((sum, item) => sum + (item.sub_answer.trim().length > 0 ? 1 : 0), 0);
}

function countSubanswersWithCitations(subQa: SubQuestionAnswer[]): number {
  return subQa.reduce((sum, item) => sum + (getSubanswerCitationIndices(item).length > 0 ? 1 : 0), 0);
}

function countTotalCitations(subQa: SubQuestionAnswer[]): number {
  return subQa.reduce((sum, item) => sum + getSubanswerCitationIndices(item).length, 0);
}

function countFallbackSubanswers(subQa: SubQuestionAnswer[]): number {
  return subQa.reduce((sum, item) => {
    const isFallback = item.sub_answer_is_fallback ?? isFallbackSubanswer(item.sub_answer);
    return sum + (isFallback ? 1 : 0);
  }, 0);
}
