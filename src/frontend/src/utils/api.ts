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

export interface WipeInternalDataResponse {
  status: "success";
  message: string;
}

export interface SubQuestionAnswer {
  sub_question: string;
  sub_answer: string;
  tool_call_input?: string;
  sub_agent_response?: string;
}

export interface RuntimeAgentRunResponse {
  output: string;
  main_question?: string;
  sub_qa?: SubQuestionAnswer[];
}

const DEFAULT_TIMEOUT_MS = 15000;
/** Agent run can take longer (LLM + RAG + subagent). */
const AGENT_RUN_TIMEOUT_MS = 180000; // 3 minutes

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
  });
}

export async function wipeInternalData(): Promise<ApiResult<WipeInternalDataResponse>> {
  return requestJson<WipeInternalDataResponse>("/api/internal-data/wipe", {
    method: "POST",
    payload: {},
    validate: (v): v is WipeInternalDataResponse =>
      isObject(v) && v.status === "success" && typeof v.message === "string",
  });
}

export async function runAgent(query: string): Promise<ApiResult<RuntimeAgentRunResponse>> {
  return requestJson<RuntimeAgentRunResponse>("/api/agents/run", {
    method: "POST",
    payload: { query },
    validate: (v): v is RuntimeAgentRunResponse => isObject(v) && typeof v.output === "string",
    timeoutMs: AGENT_RUN_TIMEOUT_MS,
  });
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
