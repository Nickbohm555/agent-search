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

export interface InternalDataLoadRequest {
  source_type?: "inline";
  documents: InternalDocumentInput[];
}

export interface InternalDataLoadResponse {
  status: "success";
  source_type: string;
  documents_loaded: number;
  chunks_created: number;
}

export interface RuntimeAgentRunRequest {
  query: string;
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
  sub_queries: string[];
  tool_assignments: SubQueryToolAssignment[];
  retrieval_results: SubQueryRetrievalResult[];
  validation_results: SubQueryValidationResult[];
  web_tool_runs: WebToolRun[];
  graph_state?: RuntimeAgentGraphState | null;
}

export interface RuntimeAgentStreamEvent {
  sequence: number;
  event:
    | "heartbeat"
    | "sub_queries"
    | "tool_assignments"
    | "subquery_execution_result"
    | "retrieval_result"
    | "validation_result"
    | "completed";
  data: Record<string, unknown>;
}

export interface RunAgentStreamHandlers {
  onEvent?: (event: RuntimeAgentStreamEvent, snapshot: RuntimeAgentRunResponse) => void;
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

export async function runAgent(
  payload: RuntimeAgentRunRequest,
  options: RequestOptions = {},
): Promise<ApiResult<RuntimeAgentRunResponse>> {
  return requestJson<RuntimeAgentRunResponse>({
    path: "/api/agents/run",
    payload,
    validate: isRuntimeAgentRunResponse,
    options,
  });
}

export async function runAgentStream(
  payload: RuntimeAgentRunRequest,
  handlers: RunAgentStreamHandlers = {},
  options: RequestOptions = {},
): Promise<ApiResult<RuntimeAgentRunResponse>> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const fetchImpl = options.fetchImpl ?? fetch;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetchImpl(`${API_BASE_URL}/api/agents/run/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

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

    if (!response.body) {
      return {
        ok: false,
        error: {
          type: "malformed_response",
          message: "Backend response did not match expected shape.",
          retryable: false,
        },
      };
    }

    const streamResult = await readSseEvents(response.body, (event, snapshot) => {
      handlers.onEvent?.(event, snapshot);
    });

    if (!streamResult.ok) {
      return streamResult;
    }

    if (!isRuntimeAgentRunResponse(streamResult.data)) {
      return {
        ok: false,
        error: {
          type: "malformed_response",
          message: "Backend response did not match expected shape.",
          retryable: false,
        },
      };
    }

    return { ok: true, data: streamResult.data };
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

interface RequestJsonArgs<T> {
  path: string;
  payload: unknown;
  validate: (value: unknown) => value is T;
  options: RequestOptions;
}

async function requestJson<T>({ path, payload, validate, options }: RequestJsonArgs<T>): Promise<ApiResult<T>> {
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const fetchImpl = options.fetchImpl ?? fetch;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetchImpl(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

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

function isToolKind(value: unknown): value is "internal" | "web" {
  return value === "internal" || value === "web";
}

function applyRuntimeStreamEvent(
  current: RuntimeAgentRunResponse,
  event: RuntimeAgentStreamEvent,
): RuntimeAgentRunResponse {
  if (event.event === "heartbeat") {
    const timelineEntry = readTimelineEntry(event.data);
    if (!timelineEntry) {
      return current;
    }
    const timeline = current.graph_state?.timeline ?? [];
    const graphState: RuntimeAgentGraphState = {
      current_step: timelineEntry.step,
      timeline: [...timeline, timelineEntry],
      graph: current.graph_state?.graph ?? {},
    };
    return { ...current, graph_state: graphState };
  }

  if (event.event === "sub_queries") {
    const subQueries = event.data.sub_queries;
    if (!isStringArray(subQueries)) {
      return current;
    }
    return { ...current, sub_queries: subQueries };
  }

  if (event.event === "tool_assignments") {
    const toolAssignments = event.data.tool_assignments;
    if (!Array.isArray(toolAssignments)) {
      return current;
    }
    const parsedAssignments = toolAssignments.filter((assignment) => {
      return (
        isObject(assignment) &&
        typeof assignment.sub_query === "string" &&
        isToolKind(assignment.tool)
      );
    }) as SubQueryToolAssignment[];
    return { ...current, tool_assignments: parsedAssignments };
  }

  if (event.event === "retrieval_result") {
    if (!isSubQueryRetrievalResult(event.data)) {
      return current;
    }
    const retrievalResults = [...current.retrieval_results, event.data];
    return {
      ...current,
      retrieval_results: retrievalResults,
      web_tool_runs: toWebToolRuns(retrievalResults),
    };
  }

  if (event.event === "validation_result") {
    if (!isSubQueryValidationResult(event.data)) {
      return current;
    }
    return {
      ...current,
      validation_results: [...current.validation_results, event.data],
    };
  }

  if (event.event === "completed") {
    const output = event.data.output;
    const agentName = event.data.agent_name;
    const graphState = event.data.graph_state;
    if (
      typeof output !== "string" ||
      typeof agentName !== "string" ||
      (graphState !== null && graphState !== undefined && !isRuntimeAgentGraphState(graphState))
    ) {
      return current;
    }
    return {
      ...current,
      agent_name: agentName,
      output,
      graph_state: (graphState as RuntimeAgentGraphState | null | undefined) ?? current.graph_state,
    };
  }

  return current;
}

async function readSseEvents(
  stream: ReadableStream<Uint8Array>,
  onEvent: (event: RuntimeAgentStreamEvent, snapshot: RuntimeAgentRunResponse) => void,
): Promise<ApiResult<RuntimeAgentRunResponse>> {
  const reader = stream.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let eventName = "";
  let eventData = "";
  let state: RuntimeAgentRunResponse = {
    agent_name: "",
    output: "",
    sub_queries: [],
    tool_assignments: [],
    retrieval_results: [],
    validation_results: [],
    web_tool_runs: [],
    graph_state: null,
  };

  const processEvent = (): ApiError | null => {
    if (!eventName || !eventData) {
      return null;
    }
    const parsed = parseRuntimeStreamEvent(eventName, eventData);
    if (!parsed.ok) {
      return parsed.error;
    }
    state = applyRuntimeStreamEvent(state, parsed.data);
    onEvent(parsed.data, state);
    eventName = "";
    eventData = "";
    return null;
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const rawLine of lines) {
      const line = rawLine.trimEnd();
      if (line.startsWith("event: ")) {
        eventName = line.slice(7).trim();
        continue;
      }
      if (line.startsWith("data: ")) {
        eventData = line.slice(6).trim();
        continue;
      }
      if (line === "" && eventName && eventData) {
        const maybeError = processEvent();
        if (maybeError) {
          return { ok: false, error: maybeError };
        }
      }
    }
  }

  const maybeError = processEvent();
  if (maybeError) {
    return { ok: false, error: maybeError };
  }

  if (!state.agent_name || !state.output) {
    return {
      ok: false,
      error: {
        type: "malformed_response",
        message: "Backend response did not match expected shape.",
        retryable: false,
      },
    };
  }

  return { ok: true, data: state };
}

function parseRuntimeStreamEvent(eventName: string, rawData: string): ApiResult<RuntimeAgentStreamEvent> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(rawData);
  } catch {
    return {
      ok: false,
      error: {
        type: "malformed_response",
        message: "Backend response did not match expected shape.",
        retryable: false,
      },
    };
  }

  if (
    !isObject(parsed) ||
    typeof parsed.sequence !== "number" ||
    typeof parsed.event !== "string" ||
    !isObject(parsed.data)
  ) {
    return {
      ok: false,
      error: {
        type: "malformed_response",
        message: "Backend response did not match expected shape.",
        retryable: false,
      },
    };
  }

  const allowedEvents = new Set([
    "heartbeat",
    "sub_queries",
    "tool_assignments",
    "subquery_execution_result",
    "retrieval_result",
    "validation_result",
    "completed",
  ]);
  if (!allowedEvents.has(parsed.event) || parsed.event !== eventName) {
    return {
      ok: false,
      error: {
        type: "malformed_response",
        message: "Backend response did not match expected shape.",
        retryable: false,
      },
    };
  }

  return { ok: true, data: parsed as unknown as RuntimeAgentStreamEvent };
}

function readTimelineEntry(data: Record<string, unknown>): RuntimeAgentGraphStep | null {
  if (
    typeof data.step !== "string" ||
    (data.status !== "started" && data.status !== "completed") ||
    !isObject(data.details)
  ) {
    return null;
  }
  return {
    step: data.step,
    status: data.status,
    details: data.details,
  };
}

function isSubQueryRetrievalResult(value: unknown): value is SubQueryRetrievalResult {
  if (!isObject(value)) {
    return false;
  }
  return (
    typeof value.sub_query === "string" &&
    isToolKind(value.tool) &&
    Array.isArray(value.internal_results) &&
    Array.isArray(value.web_search_results) &&
    isStringArray(value.opened_urls) &&
    Array.isArray(value.opened_pages)
  );
}

function isSubQueryValidationResult(value: unknown): value is SubQueryValidationResult {
  if (!isObject(value)) {
    return false;
  }
  return (
    typeof value.sub_query === "string" &&
    isToolKind(value.tool) &&
    typeof value.sufficient === "boolean" &&
    (value.status === "validated" || value.status === "stopped_insufficient") &&
    typeof value.attempts === "number" &&
    isStringArray(value.follow_up_actions) &&
    typeof value.stop_reason === "string"
  );
}

function isRuntimeAgentGraphState(value: unknown): value is RuntimeAgentGraphState {
  if (!isObject(value) || typeof value.current_step !== "string" || !Array.isArray(value.timeline)) {
    return false;
  }
  return true;
}

function toWebToolRuns(retrievalResults: SubQueryRetrievalResult[]): WebToolRun[] {
  return retrievalResults
    .filter((result) => result.tool === "web")
    .map((result) => ({
      sub_query: result.sub_query,
      search_results: result.web_search_results,
      opened_urls: result.opened_urls,
      opened_pages: result.opened_pages,
    }));
}

function isRuntimeAgentRunResponse(value: unknown): value is RuntimeAgentRunResponse {
  if (!isObject(value)) {
    return false;
  }

  if (
    typeof value.agent_name !== "string" ||
    typeof value.output !== "string" ||
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
