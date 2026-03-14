import { API_BASE_URL } from "./config";

export type RequestState = "idle" | "loading" | "success" | "error";

export interface ApiError {
  type: "http" | "network" | "timeout" | "malformed_response";
  message: string;
}

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: ApiError };

export interface WikiSourceOption {
  source_id: string;
  label: string;
  article_query: string;
  already_loaded: boolean;
}

export interface WikiSourcesResponse {
  sources: WikiSourceOption[];
}

export interface InternalDataLoadResponse {
  status: "success";
  source_type: string;
  documents_loaded: number;
  chunks_created: number;
}

export interface InternalDataLoadJobStartResponse {
  job_id: string;
  status: string;
}

export interface InternalDataLoadJobStatusResponse {
  job_id: string;
  status: string;
  total: number;
  completed: number;
  message: string;
  error?: string;
  response?: InternalDataLoadResponse;
}

export interface InternalDataLoadJobCancelResponse {
  status: "success";
  message: string;
}

export interface WipeInternalDataResponse {
  status: "success";
  message: string;
}

export interface SubQuestionAnswer {
  sub_question: string;
  sub_answer: string;
  sub_answer_citations?: number[];
  sub_answer_is_fallback?: boolean;
  tool_call_input?: string;
  sub_agent_response?: string;
  rerank_top_n?: number;
  rerank_provenance?: RerankProvenanceRow[];
  rerank_bypassed?: boolean;
}

export interface RuntimeAgentRunResponse {
  output: string;
  main_question: string;
  sub_qa: SubQuestionAnswer[];
  sub_answers?: SubQuestionAnswer[];
  final_citations: SearchCandidateRow[];
}

export type AgentStageName =
  | "decompose"
  | "expand"
  | "search"
  | "rerank"
  | "answer"
  | "final";

export type AgentStageRuntimeStatus = "pending" | "in_progress" | "completed" | "error";

export interface AgentRunStageMetadata {
  stage: string;
  status: string;
  sub_question: string;
  lane_index: number;
  lane_total: number;
  emitted_at?: number | null;
}

export interface SubQuestionArtifact {
  sub_question: string;
  expanded_queries: string[];
  retrieved_docs: SearchCandidateRow[];
  retrieval_provenance: SearchRetrievalProvenanceRow[];
  reranked_docs: SearchCandidateRow[];
}

export interface RerankProvenanceRow {
  reranked_rank: number;
  citation_index: number;
  score?: number | null;
  document_id: string;
  source: string;
}

export interface SearchCandidateRow {
  citation_index: number;
  rank: number;
  title: string;
  source: string;
  content: string;
  document_id: string;
  score?: number | null;
}

export interface SearchRetrievalProvenanceRow {
  query: string;
  query_index: number;
  query_rank: number;
  document_identity: string;
  document_id: string;
  source: string;
  deduped: boolean;
}

export interface RuntimeAgentRunAsyncStartResponse {
  job_id: string;
  run_id: string;
  status: string;
}

export interface RuntimeRerankControl {
  enabled?: boolean;
}

export interface RuntimeQueryExpansionControl {
  enabled?: boolean;
}

export interface RuntimeSubquestionHitlControl {
  enabled: boolean;
}

export interface RuntimeQueryExpansionHitlControl {
  enabled: boolean;
}

export interface RuntimeHitlControl {
  enabled: boolean;
  subquestions?: RuntimeSubquestionHitlControl;
  query_expansion?: RuntimeQueryExpansionHitlControl;
}

export interface RuntimeAgentRunControls {
  rerank?: RuntimeRerankControl;
  query_expansion?: RuntimeQueryExpansionControl;
  hitl?: RuntimeHitlControl;
}

export interface RuntimeAgentRunRuntimeConfig {
  rerank?: RuntimeRerankControl;
  query_expansion?: RuntimeQueryExpansionControl;
}

export interface RuntimeAgentRunRequest {
  query: string;
  thread_id?: string;
  controls?: RuntimeAgentRunControls;
  runtime_config?: RuntimeAgentRunRuntimeConfig;
}

export interface RuntimeSubquestionReviewItem {
  subquestion_id: string;
  sub_question: string;
  index?: number | null;
}

export interface RuntimeSubquestionPausePayload {
  checkpoint_id: string;
  stage?: string;
  kind?: string;
  subquestions: RuntimeSubquestionReviewItem[];
}

export type RuntimeSubquestionDecisionAction = "approve" | "edit" | "deny" | "skip";

export interface RuntimeSubquestionDecision {
  subquestion_id: string;
  action: RuntimeSubquestionDecisionAction;
  edited_text?: string | null;
}

export interface RuntimeSubquestionResumeEnvelope {
  checkpoint_id: string;
  decisions: RuntimeSubquestionDecision[];
}

export interface RuntimeQueryExpansionReviewItem {
  expansion_id: string;
  query: string;
  index?: number | null;
}

export interface RuntimeQueryExpansionPausePayload extends RuntimeSubquestionPausePayload {
  sub_question: string;
  expansions: RuntimeQueryExpansionReviewItem[];
}

export type RuntimeQueryExpansionDecisionAction = "approve" | "edit" | "deny" | "skip";

export interface RuntimeQueryExpansionDecision {
  expansion_id: string;
  action: RuntimeQueryExpansionDecisionAction;
  edited_query?: string | null;
}

export interface RuntimeQueryExpansionResumeEnvelope {
  checkpoint_id: string;
  decisions: RuntimeQueryExpansionDecision[];
}

export interface RuntimeAgentRunResumeRequest {
  resume:
    | boolean
    | Record<string, unknown>
    | RuntimeSubquestionResumeEnvelope
    | RuntimeQueryExpansionResumeEnvelope;
}

export interface RuntimeAgentRunAsyncStatusResponse {
  job_id: string;
  run_id: string;
  thread_id?: string;
  status: string;
  message: string;
  stage: string;
  stages: AgentRunStageMetadata[];
  decomposition_sub_questions: string[];
  sub_question_artifacts: SubQuestionArtifact[];
  sub_qa: SubQuestionAnswer[];
  sub_answers?: SubQuestionAnswer[];
  output: string;
  result?: RuntimeAgentRunResponse | null;
  error?: string | null;
  cancel_requested: boolean;
  interrupt_payload?: RuntimeSubquestionPausePayload | RuntimeQueryExpansionPausePayload | null;
  checkpoint_id?: string | null;
  started_at?: number | null;
  finished_at?: number | null;
  elapsed_ms?: number | null;
}

export interface RuntimeLifecycleEvent {
  event_type: string;
  event_id: string;
  run_id: string;
  thread_id: string;
  trace_id: string;
  stage: string;
  status: string;
  emitted_at: string;
  error?: string | null;
  decomposition_sub_questions?: string[] | null;
  sub_question_artifacts?: SubQuestionArtifact[] | null;
  sub_qa?: SubQuestionAnswer[] | null;
  sub_answers?: SubQuestionAnswer[] | null;
  output?: string | null;
  result?: RuntimeAgentRunResponse | null;
  interrupt_payload?: RuntimeSubquestionPausePayload | RuntimeQueryExpansionPausePayload | null;
  checkpoint_id?: string | null;
  elapsed_ms?: number | null;
}


const DEFAULT_TIMEOUT_MS = 15000;
const DEFAULT_AGENT_RUN_TIMEOUT_MS = 10 * 60 * 1000; // 10 minutes
const DEFAULT_INTERNAL_DATA_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes
const DEFAULT_WIPE_TIMEOUT_MS = 2 * 60 * 1000; // 2 minutes
/** Agent run can take longer (LLM + RAG + subagent). */
const AGENT_RUN_TIMEOUT_MS = parseTimeoutMs(
  import.meta.env.VITE_AGENT_RUN_TIMEOUT_MS,
  DEFAULT_AGENT_RUN_TIMEOUT_MS,
);
const INTERNAL_DATA_TIMEOUT_MS = parseTimeoutMs(
  import.meta.env.VITE_INTERNAL_DATA_TIMEOUT_MS,
  DEFAULT_INTERNAL_DATA_TIMEOUT_MS,
);
const WIPE_TIMEOUT_MS = parseTimeoutMs(
  import.meta.env.VITE_WIPE_TIMEOUT_MS,
  DEFAULT_WIPE_TIMEOUT_MS,
);

export async function listWikiSources(): Promise<ApiResult<WikiSourcesResponse>> {
  return requestJson<WikiSourcesResponse>("/api/internal-data/wiki-sources", {
    method: "GET",
    validate: (v): v is WikiSourcesResponse =>
      isObject(v) && Array.isArray(v.sources) && v.sources.every(isWikiSourceOption),
  });
}

export async function loadWikiSource(sourceId: string): Promise<ApiResult<InternalDataLoadResponse>> {
  return requestJson<InternalDataLoadResponse>("/api/internal-data/load", {
    method: "POST",
    payload: { source_type: "wiki", wiki: { source_id: sourceId } },
    validate: (v): v is InternalDataLoadResponse =>
      isObject(v) &&
      v.status === "success" &&
      typeof v.source_type === "string" &&
      typeof v.documents_loaded === "number" &&
      typeof v.chunks_created === "number",
    timeoutMs: INTERNAL_DATA_TIMEOUT_MS,
  });
}

export async function startInternalDataLoad(sourceId: string): Promise<ApiResult<InternalDataLoadJobStartResponse>> {
  return requestJson<InternalDataLoadJobStartResponse>("/api/internal-data/load-async", {
    method: "POST",
    payload: { source_type: "wiki", wiki: { source_id: sourceId } },
    validate: (v): v is InternalDataLoadJobStartResponse =>
      isObject(v) && typeof v.job_id === "string" && typeof v.status === "string",
    timeoutMs: INTERNAL_DATA_TIMEOUT_MS,
  });
}

export async function getInternalDataLoadStatus(
  jobId: string,
): Promise<ApiResult<InternalDataLoadJobStatusResponse>> {
  return requestJson<InternalDataLoadJobStatusResponse>(`/api/internal-data/load-status/${jobId}`, {
    method: "GET",
    validate: (v): v is InternalDataLoadJobStatusResponse =>
      isObject(v) &&
      typeof v.job_id === "string" &&
      typeof v.status === "string" &&
      typeof v.total === "number" &&
      typeof v.completed === "number" &&
      typeof v.message === "string" &&
      (v.error === undefined || v.error === null || typeof v.error === "string") &&
      (v.response === undefined ||
        v.response === null ||
        (isObject(v.response) &&
          v.response.status === "success" &&
          typeof v.response.source_type === "string" &&
          typeof v.response.documents_loaded === "number" &&
          typeof v.response.chunks_created === "number")),
    timeoutMs: INTERNAL_DATA_TIMEOUT_MS,
  });
}

export async function cancelInternalDataLoad(jobId: string): Promise<ApiResult<InternalDataLoadJobCancelResponse>> {
  return requestJson<InternalDataLoadJobCancelResponse>(`/api/internal-data/load-cancel/${jobId}`, {
    method: "POST",
    payload: {},
    validate: (v): v is InternalDataLoadJobCancelResponse =>
      isObject(v) && v.status === "success" && typeof v.message === "string",
    timeoutMs: INTERNAL_DATA_TIMEOUT_MS,
  });
}

export async function wipeInternalData(): Promise<ApiResult<WipeInternalDataResponse>> {
  return requestJson<WipeInternalDataResponse>("/api/internal-data/wipe", {
    method: "POST",
    payload: {},
    validate: (v): v is WipeInternalDataResponse =>
      isObject(v) && v.status === "success" && typeof v.message === "string",
    timeoutMs: WIPE_TIMEOUT_MS,
  });
}

export async function runAgent(query: string): Promise<ApiResult<RuntimeAgentRunResponse>> {
  return requestJson<RuntimeAgentRunResponse>("/api/agents/run", {
    method: "POST",
    payload: { query },
    validate: (v): v is RuntimeAgentRunResponse => validateRuntimeAgentRunResponse(v),
    timeoutMs: AGENT_RUN_TIMEOUT_MS,
  });
}

export function buildRuntimeAgentRunRequest(
  query: string,
  options: Omit<RuntimeAgentRunRequest, "query"> = {},
): RuntimeAgentRunRequest {
  const payload: RuntimeAgentRunRequest = { query };
  if (typeof options.thread_id === "string" && options.thread_id.trim()) {
    payload.thread_id = options.thread_id.trim();
  }
  if (options.controls !== undefined) {
    payload.controls = options.controls;
  }
  if (options.runtime_config !== undefined) {
    payload.runtime_config = options.runtime_config;
  }
  return payload;
}

export async function startAgentRun(
  query: string,
  options: Omit<RuntimeAgentRunRequest, "query"> = {},
): Promise<ApiResult<RuntimeAgentRunAsyncStartResponse>> {
  return requestJson<RuntimeAgentRunAsyncStartResponse>("/api/agents/run-async", {
    method: "POST",
    payload: buildRuntimeAgentRunRequest(query, options),
    validate: (v): v is RuntimeAgentRunAsyncStartResponse =>
      isObject(v) &&
      typeof v.job_id === "string" &&
      typeof v.run_id === "string" &&
      typeof v.status === "string",
    timeoutMs: AGENT_RUN_TIMEOUT_MS,
  });
}

export function buildRuntimeAgentRunResumeRequest(
  resume: RuntimeAgentRunResumeRequest["resume"] = true,
): RuntimeAgentRunResumeRequest {
  return { resume };
}

export async function resumeAgentRun(
  jobId: string,
  resume: RuntimeAgentRunResumeRequest["resume"] = true,
): Promise<ApiResult<RuntimeAgentRunAsyncStatusResponse>> {
  return requestJson<RuntimeAgentRunAsyncStatusResponse>(`/api/agents/run-resume/${jobId}`, {
    method: "POST",
    payload: buildRuntimeAgentRunResumeRequest(resume),
    validate: (v): v is RuntimeAgentRunAsyncStatusResponse => isRuntimeAgentRunAsyncStatusResponse(v),
    timeoutMs: AGENT_RUN_TIMEOUT_MS,
  });
}

export async function getAgentRunStatus(jobId: string): Promise<ApiResult<RuntimeAgentRunAsyncStatusResponse>> {
  return requestJson<RuntimeAgentRunAsyncStatusResponse>(`/api/agents/run-status/${jobId}`, {
    method: "GET",
    validate: (v): v is RuntimeAgentRunAsyncStatusResponse => isRuntimeAgentRunAsyncStatusResponse(v),
    timeoutMs: AGENT_RUN_TIMEOUT_MS,
  });
}

export function subscribeToAgentRunEvents(
  jobId: string,
  handlers: {
    onEvent: (event: RuntimeLifecycleEvent) => void;
    onError?: () => void;
  },
): () => void {
  const eventSource = new EventSource(`${API_BASE_URL}/api/agents/run-events/${jobId}`);
  const eventTypes = [
    "stage.started",
    "stage.updated",
    "stage.retrying",
    "stage.completed",
    "stage.failed",
    "run.completed",
    "run.failed",
    "run.paused",
  ] as const;

  const handleMessage = (message: MessageEvent<string>) => {
    try {
      const payload: unknown = JSON.parse(message.data);
      if (isRuntimeLifecycleEvent(payload)) {
        handlers.onEvent(payload);
      }
    } catch {
      return;
    }
  };

  eventSource.onmessage = handleMessage;
  for (const eventType of eventTypes) {
    eventSource.addEventListener(eventType, handleMessage as EventListener);
  }
  eventSource.onerror = () => {
    handlers.onError?.();
  };

  return () => {
    for (const eventType of eventTypes) {
      eventSource.removeEventListener(eventType, handleMessage as EventListener);
    }
    eventSource.close();
  };
}


function parseTimeoutMs(value: unknown, fallbackMs: number): number {
  if (typeof value !== "string" || value.trim().length === 0) return fallbackMs;
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallbackMs;
  return Math.floor(parsed);
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isWikiSourceOption(value: unknown): value is WikiSourceOption {
  return (
    isObject(value) &&
    typeof value.source_id === "string" &&
    typeof value.label === "string" &&
    typeof value.article_query === "string" &&
    typeof value.already_loaded === "boolean"
  );
}

function isOptionalString(value: unknown): value is string | undefined {
  return value === undefined || typeof value === "string";
}


function isSubQuestionAnswer(value: unknown): value is SubQuestionAnswer {
  if (
    isObject(value) &&
    typeof value.sub_question === "string" &&
    typeof value.sub_answer === "string" &&
    isOptionalString(value.tool_call_input) &&
    isOptionalString(value.sub_agent_response)
  ) {
    attachSubanswerMetadata(value);
    attachRerankMetadataFromToolCallInput(value);
    return (
      (value.sub_answer_citations === undefined ||
        (Array.isArray(value.sub_answer_citations) &&
          value.sub_answer_citations.every((item) => typeof item === "number"))) &&
      (value.sub_answer_is_fallback === undefined || typeof value.sub_answer_is_fallback === "boolean") &&
      (value.rerank_top_n === undefined || typeof value.rerank_top_n === "number") &&
      (value.rerank_bypassed === undefined || typeof value.rerank_bypassed === "boolean") &&
      (value.rerank_provenance === undefined ||
        (Array.isArray(value.rerank_provenance) && value.rerank_provenance.every(isRerankProvenanceRow)))
    );
  }
  return false;
}

function isAgentRunStageMetadata(value: unknown): value is AgentRunStageMetadata {
  return (
    isObject(value) &&
    typeof value.stage === "string" &&
    typeof value.status === "string" &&
    typeof value.sub_question === "string" &&
    typeof value.lane_index === "number" &&
    typeof value.lane_total === "number" &&
    (value.emitted_at === undefined || value.emitted_at === null || typeof value.emitted_at === "number")
  );
}

function isRuntimeAgentRunAsyncStatusResponse(value: unknown): value is RuntimeAgentRunAsyncStatusResponse {
  return (
    isObject(value) &&
    typeof value.job_id === "string" &&
    typeof value.run_id === "string" &&
    (value.thread_id === undefined || typeof value.thread_id === "string") &&
    typeof value.status === "string" &&
    typeof value.message === "string" &&
    typeof value.stage === "string" &&
    Array.isArray(value.stages) &&
    value.stages.every(isAgentRunStageMetadata) &&
    Array.isArray(value.decomposition_sub_questions) &&
    value.decomposition_sub_questions.every((item) => typeof item === "string") &&
    Array.isArray(value.sub_question_artifacts) &&
    value.sub_question_artifacts.every(isSubQuestionArtifact) &&
    Array.isArray(value.sub_qa) &&
    value.sub_qa.every(isSubQuestionAnswer) &&
    (value.sub_answers === undefined ||
      (Array.isArray(value.sub_answers) && value.sub_answers.every(isSubQuestionAnswer))) &&
    typeof value.output === "string" &&
    (value.result === undefined || value.result === null || validateRuntimeAgentRunResponse(value.result)) &&
    (value.error === undefined || value.error === null || typeof value.error === "string") &&
    typeof value.cancel_requested === "boolean" &&
    (value.interrupt_payload === undefined ||
      value.interrupt_payload === null ||
      isRuntimePausePayload(value.interrupt_payload, value.checkpoint_id)) &&
    (value.checkpoint_id === undefined || value.checkpoint_id === null || typeof value.checkpoint_id === "string") &&
    (value.started_at === undefined || value.started_at === null || typeof value.started_at === "number") &&
    (value.finished_at === undefined || value.finished_at === null || typeof value.finished_at === "number") &&
    (value.elapsed_ms === undefined || value.elapsed_ms === null || typeof value.elapsed_ms === "number")
  );
}

function isRuntimeLifecycleEvent(value: unknown): value is RuntimeLifecycleEvent {
  return (
    isObject(value) &&
    typeof value.event_type === "string" &&
    typeof value.event_id === "string" &&
    typeof value.run_id === "string" &&
    typeof value.thread_id === "string" &&
    typeof value.trace_id === "string" &&
    typeof value.stage === "string" &&
    typeof value.status === "string" &&
    typeof value.emitted_at === "string" &&
    (value.error === undefined || value.error === null || typeof value.error === "string") &&
    (value.decomposition_sub_questions === undefined ||
      value.decomposition_sub_questions === null ||
      (Array.isArray(value.decomposition_sub_questions) &&
        value.decomposition_sub_questions.every((item) => typeof item === "string"))) &&
    (value.sub_question_artifacts === undefined ||
      value.sub_question_artifacts === null ||
      (Array.isArray(value.sub_question_artifacts) && value.sub_question_artifacts.every(isSubQuestionArtifact))) &&
    (value.sub_qa === undefined || value.sub_qa === null || (Array.isArray(value.sub_qa) && value.sub_qa.every(isSubQuestionAnswer))) &&
    (value.sub_answers === undefined ||
      value.sub_answers === null ||
      (Array.isArray(value.sub_answers) && value.sub_answers.every(isSubQuestionAnswer))) &&
    (value.output === undefined || value.output === null || typeof value.output === "string") &&
    (value.result === undefined || value.result === null || validateRuntimeAgentRunResponse(value.result)) &&
    (value.interrupt_payload === undefined ||
      value.interrupt_payload === null ||
      isRuntimePausePayload(value.interrupt_payload, value.checkpoint_id)) &&
    (value.checkpoint_id === undefined || value.checkpoint_id === null || typeof value.checkpoint_id === "string") &&
    (value.elapsed_ms === undefined || value.elapsed_ms === null || typeof value.elapsed_ms === "number")
  );
}

function isRuntimePausePayload(
  value: unknown,
  parentCheckpointId?: unknown,
): value is RuntimeSubquestionPausePayload | RuntimeQueryExpansionPausePayload {
  return (
    isRuntimeSubquestionPausePayload(value, parentCheckpointId) ||
    isRuntimeQueryExpansionPausePayload(value, parentCheckpointId)
  );
}

function isRuntimeSubquestionPausePayload(
  value: unknown,
  parentCheckpointId?: unknown,
): value is RuntimeSubquestionPausePayload {
  if (!isObject(value)) return false;

  const rawCheckpointId =
    typeof value.checkpoint_id === "string" && value.checkpoint_id.trim()
      ? value.checkpoint_id
      : typeof parentCheckpointId === "string" && parentCheckpointId.trim()
        ? parentCheckpointId
        : null;
  if (rawCheckpointId === null) return false;

  const normalizedSubquestions = normalizeRuntimeSubquestionReviewItems(value);
  if (normalizedSubquestions === null) return false;

  value.checkpoint_id = rawCheckpointId;
  value.subquestions = normalizedSubquestions;
  return (
    (value.stage === undefined || typeof value.stage === "string") &&
    (value.kind === undefined || typeof value.kind === "string")
  );
}

function isRuntimeQueryExpansionPausePayload(
  value: unknown,
  parentCheckpointId?: unknown,
): value is RuntimeQueryExpansionPausePayload {
  if (!isObject(value)) return false;

  const rawCheckpointId =
    typeof value.checkpoint_id === "string" && value.checkpoint_id.trim()
      ? value.checkpoint_id
      : typeof parentCheckpointId === "string" && parentCheckpointId.trim()
        ? parentCheckpointId
        : null;
  if (rawCheckpointId === null) return false;

  const subQuestion =
    typeof value.sub_question === "string" && value.sub_question.trim()
      ? value.sub_question
      : typeof value.question === "string" && value.question.trim()
        ? value.question
        : null;
  if (subQuestion === null) return false;

  const normalizedExpansions = normalizeRuntimeQueryExpansionReviewItems(value);
  if (normalizedExpansions === null) return false;

  value.checkpoint_id = rawCheckpointId;
  value.sub_question = subQuestion;
  value.expansions = normalizedExpansions;
  value.subquestions = normalizedExpansions.map((item) => ({
    subquestion_id: item.expansion_id,
    sub_question: item.query,
    index: item.index ?? null,
  }));
  return (
    (value.stage === undefined || typeof value.stage === "string") &&
    (value.kind === undefined || typeof value.kind === "string")
  );
}

function normalizeRuntimeSubquestionReviewItems(value: Record<string, unknown>): RuntimeSubquestionReviewItem[] | null {
  const rawItems = value.subquestions ?? value.proposed_subquestions;
  if (!Array.isArray(rawItems)) return null;

  const normalizedItems: RuntimeSubquestionReviewItem[] = [];
  for (let index = 0; index < rawItems.length; index += 1) {
    const normalizedItem = normalizeRuntimeSubquestionReviewItem(rawItems[index], index);
    if (normalizedItem === null) return null;
    normalizedItems.push(normalizedItem);
  }
  return normalizedItems;
}

function normalizeRuntimeSubquestionReviewItem(
  value: unknown,
  fallbackIndex: number,
): RuntimeSubquestionReviewItem | null {
  if (!isObject(value)) return null;

  const subquestionId =
    typeof value.subquestion_id === "string" && value.subquestion_id.trim()
      ? value.subquestion_id
      : typeof value.id === "string" && value.id.trim()
        ? value.id
        : typeof value.index === "number"
          ? `index:${value.index}`
          : `index:${fallbackIndex}`;

  const subQuestion =
    typeof value.sub_question === "string" && value.sub_question.trim()
      ? value.sub_question
      : typeof value.question === "string" && value.question.trim()
        ? value.question
        : typeof value.text === "string" && value.text.trim()
          ? value.text
          : null;
  if (subQuestion === null) return null;

  return {
    subquestion_id: subquestionId,
    sub_question: subQuestion,
    index: typeof value.index === "number" ? value.index : fallbackIndex,
  };
}

function normalizeRuntimeQueryExpansionReviewItems(
  value: Record<string, unknown>,
): RuntimeQueryExpansionReviewItem[] | null {
  const rawItems = value.expansions;
  if (!Array.isArray(rawItems)) return null;

  const normalizedItems: RuntimeQueryExpansionReviewItem[] = [];
  for (let index = 0; index < rawItems.length; index += 1) {
    const normalizedItem = normalizeRuntimeQueryExpansionReviewItem(rawItems[index], index);
    if (normalizedItem === null) return null;
    normalizedItems.push(normalizedItem);
  }
  return normalizedItems;
}

function normalizeRuntimeQueryExpansionReviewItem(
  value: unknown,
  fallbackIndex: number,
): RuntimeQueryExpansionReviewItem | null {
  if (!isObject(value)) return null;

  const expansionId =
    typeof value.expansion_id === "string" && value.expansion_id.trim()
      ? value.expansion_id
      : typeof value.id === "string" && value.id.trim()
        ? value.id
        : typeof value.index === "number"
          ? `expansion:${value.index}`
          : `expansion:${fallbackIndex}`;

  const query =
    typeof value.query === "string" && value.query.trim()
      ? value.query
      : typeof value.text === "string" && value.text.trim()
        ? value.text
        : null;
  if (query === null) return null;

  return {
    expansion_id: expansionId,
    query,
    index: typeof value.index === "number" ? value.index : fallbackIndex,
  };
}

function isSubQuestionArtifact(value: unknown): value is SubQuestionArtifact {
  if (!isObject(value)) return false;
  const expandedQueries = value.expanded_queries;
  if (value.retrieved_docs === undefined) value.retrieved_docs = [];
  if (value.retrieval_provenance === undefined) value.retrieval_provenance = [];
  if (value.reranked_docs === undefined) value.reranked_docs = [];
  const retrievedDocs = value.retrieved_docs;
  const retrievalProvenance = value.retrieval_provenance;
  const rerankedDocs = value.reranked_docs;
  return (
    typeof value.sub_question === "string" &&
    Array.isArray(expandedQueries) &&
    expandedQueries.every((item) => typeof item === "string") &&
    (retrievedDocs === undefined || (Array.isArray(retrievedDocs) && retrievedDocs.every(isSearchCandidateRow))) &&
    (rerankedDocs === undefined || (Array.isArray(rerankedDocs) && rerankedDocs.every(isSearchCandidateRow))) &&
    (retrievalProvenance === undefined ||
      (Array.isArray(retrievalProvenance) && retrievalProvenance.every(isSearchRetrievalProvenanceRow)))
  );
}

function attachSubanswerMetadata(value: Record<string, unknown>): void {
  const rawSubAnswer = value.sub_answer;
  if (typeof rawSubAnswer !== "string") return;
  const citations = extractCitationIndices(rawSubAnswer);
  if (citations.length > 0) {
    value.sub_answer_citations = citations;
  }
  value.sub_answer_is_fallback = rawSubAnswer.trim().toLowerCase() === "nothing relevant found";
}

function extractCitationIndices(text: string): number[] {
  const matches = text.matchAll(/\[(\d+)\]/g);
  const values = Array.from(matches, (match) => Number(match[1])).filter((item) => Number.isInteger(item) && item > 0);
  return Array.from(new Set(values));
}

function attachRerankMetadataFromToolCallInput(value: Record<string, unknown>): void {
  const rawToolCallInput = value.tool_call_input;
  if (typeof rawToolCallInput !== "string" || !rawToolCallInput.trim()) return;

  try {
    const parsed: unknown = JSON.parse(rawToolCallInput);
    if (!isObject(parsed)) return;

    const rerankTopN = parsed.rerank_top_n;
    if (typeof rerankTopN === "number") {
      value.rerank_top_n = rerankTopN;
    }

    const rerankProvenance = parsed.rerank_provenance;
    if (Array.isArray(rerankProvenance) && rerankProvenance.every(isRerankProvenanceRow)) {
      value.rerank_provenance = rerankProvenance;
      if (rerankProvenance.length > 0) {
        value.rerank_bypassed = rerankProvenance.every((row) => row.score === null || row.score === undefined);
      }
    }
  } catch {
    return;
  }
}

function isRerankProvenanceRow(value: unknown): value is RerankProvenanceRow {
  return (
    isObject(value) &&
    typeof value.reranked_rank === "number" &&
    typeof value.citation_index === "number" &&
    (value.score === undefined || value.score === null || typeof value.score === "number") &&
    typeof value.document_id === "string" &&
    typeof value.source === "string"
  );
}

function isSearchCandidateRow(value: unknown): value is SearchCandidateRow {
  return (
    isObject(value) &&
    typeof value.citation_index === "number" &&
    typeof value.rank === "number" &&
    typeof value.title === "string" &&
    typeof value.source === "string" &&
    typeof value.content === "string" &&
    typeof value.document_id === "string" &&
    (value.score === undefined || value.score === null || typeof value.score === "number")
  );
}

function isSearchRetrievalProvenanceRow(value: unknown): value is SearchRetrievalProvenanceRow {
  return (
    isObject(value) &&
    typeof value.query === "string" &&
    typeof value.query_index === "number" &&
    typeof value.query_rank === "number" &&
    typeof value.document_identity === "string" &&
    typeof value.document_id === "string" &&
    typeof value.source === "string" &&
    typeof value.deduped === "boolean"
  );
}

function validateRuntimeAgentRunResponse(value: unknown): value is RuntimeAgentRunResponse {
  if (!isObject(value) || typeof value.output !== "string") return false;

  if (value.main_question === undefined) {
    value.main_question = "";
  } else if (typeof value.main_question !== "string") {
    console.warn("runAgent response validation failed: main_question must be a string.");
    return false;
  }

  if (value.sub_qa === undefined) {
    value.sub_qa = [];
  } else if (!Array.isArray(value.sub_qa) || !value.sub_qa.every(isSubQuestionAnswer)) {
    console.warn("runAgent response validation failed: sub_qa must be an array of sub-question objects.");
    return false;
  }

  if (value.sub_answers !== undefined) {
    if (!Array.isArray(value.sub_answers) || !value.sub_answers.every(isSubQuestionAnswer)) {
      console.warn("runAgent response validation failed: sub_answers must be an array of sub-question objects.");
      return false;
    }
  }

  if (value.final_citations === undefined) {
    value.final_citations = [];
  } else if (!Array.isArray(value.final_citations) || !value.final_citations.every(isSearchCandidateRow)) {
    console.warn("runAgent response validation failed: final_citations must be an array of citations.");
    return false;
  }

  return true;
}

async function requestJson<T>(
  path: string,
  args: {
    method: "GET" | "POST";
    validate: (value: unknown) => value is T;
    payload?: unknown;
    timeoutMs?: number;
  },
): Promise<ApiResult<T>> {
  const controller = new AbortController();
  const timeoutMs = args.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: args.method,
      signal: controller.signal,
      headers: args.method === "POST" ? { "Content-Type": "application/json" } : undefined,
      body: args.method === "POST" ? JSON.stringify(args.payload ?? {}) : undefined,
    });

    if (!response.ok) {
      return {
        ok: false,
        error: { type: "http", message: `Request failed with status ${response.status}` },
      };
    }

    const data: unknown = await response.json();
    if (!args.validate(data)) {
      return {
        ok: false,
        error: { type: "malformed_response", message: "Response did not match expected shape." },
      };
    }

    return { ok: true, data };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return { ok: false, error: { type: "timeout", message: "Request timed out." } };
    }
    return { ok: false, error: { type: "network", message: "Network error." } };
  } finally {
    clearTimeout(timeoutId);
  }
}
