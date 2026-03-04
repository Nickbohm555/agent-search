import { API_BASE_URL } from "./config";

const DEFAULT_TIMEOUT_MS = 15000;

export type ApiErrorType = "http" | "network" | "timeout" | "malformed_response";

export interface ApiError {
  type: ApiErrorType;
  message: string;
  retryable: boolean;
  statusCode?: number;
}

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: ApiError };

export interface InternalDocumentInput {
  title: string;
  content: string;
  source_ref?: string;
}

export interface WikiLoadInput {
  source_id: string;
}

export interface WikiSourceOption {
  source_id: string;
  label: string;
  article_query: string;
  already_loaded: boolean;
}

export interface WikiSourcesResponse {
  sources: WikiSourceOption[];
}

export type InternalDataLoadRequest =
  | {
      source_type?: "inline";
      documents: InternalDocumentInput[];
      wiki?: never;
    }
  | {
      source_type: "wiki";
      wiki: WikiLoadInput;
      documents?: never;
    };

export interface InternalDataLoadResponse {
  status: "success";
  source_type: string;
  documents_loaded: number;
  chunks_created: number;
}

export interface RuntimeAgentRunRequest {
  query: string;
  thread_id?: string;
  user_id?: string;
  checkpoint_id?: string;
}

export interface SubQueryToolAssignment {
  sub_query: string;
  tool: "internal" | "web";
}

export interface InternalRetrievedChunk {
  chunk_id: number;
  document_id: number;
  document_title: string;
  source_type: string;
  source_ref?: string | null;
  content: string;
  score: number;
  chunk_metadata?: {
    source: string;
    topic: string;
  } | null;
}

export interface WebSearchResult {
  title: string;
  url: string;
  snippet: string;
}

export interface WebOpenUrlResponse {
  url: string;
  title?: string;
  content: string;
}

export interface SubQueryRetrievalResult {
  sub_query: string;
  tool: "internal" | "web";
  internal_results: InternalRetrievedChunk[];
  web_search_results: WebSearchResult[];
  opened_urls: string[];
  opened_pages: WebOpenUrlResponse[];
}

export interface SubQueryValidationResult {
  sub_query: string;
  tool: "internal" | "web";
  sufficient: boolean;
  status: "validated" | "stopped_insufficient";
  attempts: number;
  follow_up_actions: string[];
  stop_reason: string;
}

export interface WebToolRun {
  sub_query: string;
  search_results: WebSearchResult[];
  opened_urls: string[];
  opened_pages: WebOpenUrlResponse[];
}

export interface RuntimeAgentGraphStep {
  step: string;
  status: "started" | "completed";
  details: Record<string, unknown>;
}

export interface RuntimeAgentGraphState {
  current_step: string;
  timeline: RuntimeAgentGraphStep[];
  graph: Record<string, unknown>;
}

export interface RuntimeAgentRunResponse {
  agent_name: string;
  output: string;
  thread_id: string;
  checkpoint_id?: string | null;
  sub_queries: string[];
  tool_assignments: SubQueryToolAssignment[];
  retrieval_results: SubQueryRetrievalResult[];
  validation_results: SubQueryValidationResult[];
  web_tool_runs: WebToolRun[];
  graph_state?: RuntimeAgentGraphState | null;
}

interface RequestOptions {
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
}

export async function loadInternalData(
  payload: InternalDataLoadRequest,
  options: RequestOptions = {},
): Promise<ApiResult<InternalDataLoadResponse>> {
  return requestJson<InternalDataLoadResponse>({
    path: "/api/internal-data/load",
    payload,
    validate: isInternalDataLoadResponse,
    options,
  });
}

export async function listWikiSources(options: RequestOptions = {}): Promise<ApiResult<WikiSourcesResponse>> {
  return requestJson<WikiSourcesResponse>({
    path: "/api/internal-data/wiki-sources",
    method: "GET",
    validate: isWikiSourcesResponse,
    options,
  });
}

export async function runAgent(
  payload: RuntimeAgentRunRequest,
  options: RequestOptions = {},
): Promise<ApiResult<RuntimeAgentRunResponse>> {
  // Called by `App.handleRun` to execute one agent run with optional persistence context.
  // Sends a POST request to `/api/agents/run` and returns either validated response data
  // or a deterministic API error result without throwing.
  return requestJson<RuntimeAgentRunResponse>({
    path: "/api/agents/run",
    payload,
    validate: isRuntimeAgentRunResponse,
    options,
  });
}

interface RequestJsonArgs<T> {
  path: string;
  payload?: unknown;
  method?: "GET" | "POST";
  validate: (value: unknown) => value is T;
  options: RequestOptions;
}

async function requestJson<T>({ path, payload, method = "POST", validate, options }: RequestJsonArgs<T>): Promise<ApiResult<T>> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const fetchImpl = options.fetchImpl ?? fetch;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const requestInit: RequestInit = {
      method,
      signal: controller.signal,
    };
    if (method !== "GET") {
      requestInit.headers = { "Content-Type": "application/json" };
      requestInit.body = JSON.stringify(payload);
    }
    const response = await fetchImpl(`${API_BASE_URL}${path}`, requestInit);

    if (!response.ok) {
      await safeReadText(response);
      return {
        ok: false,
        error: {
          type: "http",
          message: `Request failed with status ${response.status}`,
          retryable: response.status >= 500,
          statusCode: response.status,
        },
      };
    }

    const data: unknown = await response.json();
    if (!validate(data)) {
      return {
        ok: false,
        error: {
          type: "malformed_response",
          message: "Backend response did not match expected shape.",
          retryable: false,
        },
      };
    }

    return { ok: true, data };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return {
        ok: false,
        error: {
          type: "timeout",
          message: "Request timed out. Please retry.",
          retryable: true,
        },
      };
    }

    return {
      ok: false,
      error: {
        type: "network",
        message: "Network error. Please check connection and retry.",
        retryable: true,
      },
    };
  } finally {
    clearTimeout(timeoutId);
  }
}

async function safeReadText(response: Response): Promise<string> {
  try {
    return await response.text();
  } catch {
    return "";
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((entry) => typeof entry === "string");
}

function isInternalDataLoadResponse(value: unknown): value is InternalDataLoadResponse {
  if (!isObject(value)) {
    return false;
  }

  return (
    value.status === "success" &&
    typeof value.source_type === "string" &&
    typeof value.documents_loaded === "number" &&
    typeof value.chunks_created === "number"
  );
}

function isWikiSourcesResponse(value: unknown): value is WikiSourcesResponse {
  if (!isObject(value) || !Array.isArray(value.sources)) {
    return false;
  }

  return value.sources.every((source) => {
    return (
      isObject(source) &&
      typeof source.source_id === "string" &&
      source.source_id.trim().length > 0 &&
      typeof source.label === "string" &&
      source.label.trim().length > 0 &&
      typeof source.article_query === "string" &&
      source.article_query.trim().length > 0 &&
      typeof source.already_loaded === "boolean"
    );
  });
}

function isToolKind(value: unknown): value is "internal" | "web" {
  return value === "internal" || value === "web";
}

function isChunkMetadata(value: unknown): value is { source: string; topic: string } {
  if (!isObject(value)) {
    return false;
  }

  return typeof value.source === "string" && typeof value.topic === "string";
}

function isInternalRetrievedChunk(value: unknown): value is InternalRetrievedChunk {
  // Called by runtime response validation to keep internal retrieval readouts
  // type-safe when chunk attribution metadata is included.
  if (!isObject(value)) {
    return false;
  }

  return (
    typeof value.chunk_id === "number" &&
    typeof value.document_id === "number" &&
    typeof value.document_title === "string" &&
    typeof value.source_type === "string" &&
    (value.source_ref === undefined || value.source_ref === null || typeof value.source_ref === "string") &&
    typeof value.content === "string" &&
    typeof value.score === "number" &&
    (value.chunk_metadata === undefined || value.chunk_metadata === null || isChunkMetadata(value.chunk_metadata))
  );
}

function isWebSearchResult(value: unknown): value is WebSearchResult {
  return (
    isObject(value) &&
    typeof value.title === "string" &&
    typeof value.url === "string" &&
    typeof value.snippet === "string"
  );
}

function isWebOpenUrlResponse(value: unknown): value is WebOpenUrlResponse {
  return (
    isObject(value) &&
    typeof value.url === "string" &&
    (value.title === undefined || typeof value.title === "string") &&
    typeof value.content === "string"
  );
}

function isSubQueryRetrievalResult(value: unknown): value is SubQueryRetrievalResult {
  // Validates retrieval payload blocks so malformed nested arrays do not enter
  // frontend state during `/api/agents/run` response handling.
  return (
    isObject(value) &&
    typeof value.sub_query === "string" &&
    isToolKind(value.tool) &&
    Array.isArray(value.internal_results) &&
    value.internal_results.every(isInternalRetrievedChunk) &&
    Array.isArray(value.web_search_results) &&
    value.web_search_results.every(isWebSearchResult) &&
    isStringArray(value.opened_urls) &&
    Array.isArray(value.opened_pages) &&
    value.opened_pages.every(isWebOpenUrlResponse)
  );
}

function isRuntimeAgentRunResponse(value: unknown): value is RuntimeAgentRunResponse {
  // Used by `requestJson` in `runAgent` so UI state only receives shape-safe payloads.
  // Side effect free: validates runtime payload structure, including persistence IDs.
  if (!isObject(value)) {
    return false;
  }

  if (
    typeof value.agent_name !== "string" ||
    typeof value.output !== "string" ||
    typeof value.thread_id !== "string" ||
    value.thread_id.trim().length === 0 ||
    (value.checkpoint_id !== undefined &&
      value.checkpoint_id !== null &&
      typeof value.checkpoint_id !== "string") ||
    !isStringArray(value.sub_queries) ||
    !Array.isArray(value.tool_assignments) ||
    !Array.isArray(value.retrieval_results) ||
    !Array.isArray(value.validation_results) ||
    !Array.isArray(value.web_tool_runs)
  ) {
    return false;
  }

  const validToolAssignments = value.tool_assignments.every((assignment) => {
    return (
      isObject(assignment) &&
      typeof assignment.sub_query === "string" &&
      isToolKind(assignment.tool)
    );
  });

  if (!validToolAssignments) {
    return false;
  }

  const validValidationResults = value.validation_results.every((result) => {
    return (
      isObject(result) &&
      typeof result.sub_query === "string" &&
      isToolKind(result.tool) &&
      typeof result.sufficient === "boolean" &&
      (result.status === "validated" || result.status === "stopped_insufficient") &&
      typeof result.attempts === "number" &&
      isStringArray(result.follow_up_actions) &&
      typeof result.stop_reason === "string"
    );
  });

  if (!validValidationResults) {
    return false;
  }

  const validRetrievalResults = value.retrieval_results.every((result) => {
    return isSubQueryRetrievalResult(result);
  });

  if (!validRetrievalResults) {
    return false;
  }

  const graphState = value.graph_state;
  if (graphState !== undefined && graphState !== null) {
    if (!isObject(graphState) || typeof graphState.current_step !== "string") {
      return false;
    }

    if (!Array.isArray(graphState.timeline)) {
      return false;
    }
  }

  return true;
}
