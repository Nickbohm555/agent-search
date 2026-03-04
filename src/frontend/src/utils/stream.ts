import { API_BASE_URL } from "./config";
import { ApiResult, ApiError, RuntimeAgentRunRequest } from "./api";
import {
  RuntimeAgentStreamCompletedData,
  RuntimeAgentStreamEvent,
  isRuntimeAgentStreamEvent,
} from "../lib/stream-events";

const DEFAULT_STREAM_TIMEOUT_MS = 30000;

export interface RuntimeAgentStreamResponse {
  events: RuntimeAgentStreamEvent[];
  completed: RuntimeAgentStreamCompletedData;
}

interface StreamRequestOptions {
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
  onEvent?: (event: RuntimeAgentStreamEvent) => void;
}

export async function streamAgentRun(
  payload: RuntimeAgentRunRequest,
  options: StreamRequestOptions = {},
): Promise<ApiResult<RuntimeAgentStreamResponse>> {
  // Called by the UI run flow to consume POST `/api/agents/run/stream` SSE frames.
  // Parses and validates ordered events, forwarding each to `onEvent`, and returns
  // a deterministic error object instead of throwing on malformed/interrupted streams.
  const timeoutMs = options.timeoutMs ?? DEFAULT_STREAM_TIMEOUT_MS;
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

    const contentType = response.headers.get("Content-Type") ?? "";
    if (!contentType.includes("text/event-stream") || response.body === null) {
      return malformedResponse("Stream response was not a valid event stream.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let lastSequence = 0;
    let sawHeartbeat = false;
    let sawSubQueries = false;
    let completed: RuntimeAgentStreamCompletedData | null = null;
    const events: RuntimeAgentStreamEvent[] = [];

    while (true) {
      const readResult = await reader.read();
      if (readResult.done) {
        break;
      }

      buffer += decoder.decode(readResult.value, { stream: true });
      const parsed = consumeSseFrames(buffer);
      buffer = parsed.remainder;

      for (const frame of parsed.frames) {
        if (frame.trim().length === 0) {
          continue;
        }

        const eventParse = parseSseDataFrame(frame);
        if (!eventParse.ok) {
          return eventParse;
        }

        const event = eventParse.data;
        if (event.sequence <= lastSequence) {
          return malformedResponse("Stream events arrived out of order.");
        }

        if (!sawHeartbeat && event.event !== "heartbeat") {
          return malformedResponse("Stream must start with a heartbeat event.");
        }

        if (event.event === "heartbeat") {
          sawHeartbeat = true;
        }

        if (event.event === "sub_queries") {
          sawSubQueries = true;
        }

        if (event.event === "completed") {
          if (!sawSubQueries) {
            return malformedResponse("Completed event arrived before sub_queries.");
          }
          if (completed !== null) {
            return malformedResponse("Stream included multiple completed events.");
          }
          completed = event.data;
        }

        lastSequence = event.sequence;
        events.push(event);
        options.onEvent?.(event);
      }
    }

    if (completed === null) {
      return {
        ok: false,
        error: {
          type: "network",
          message: "Stream interrupted before completion. Please retry.",
          retryable: true,
        },
      };
    }

    return { ok: true, data: { events, completed } };
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

function consumeSseFrames(buffer: string): { frames: string[]; remainder: string } {
  // Called by `streamAgentRun` after each chunk read to split complete SSE frames
  // from partial trailing text that must be preserved for the next read.
  const chunks = buffer.split("\n\n");
  const remainder = chunks.pop() ?? "";
  return { frames: chunks, remainder };
}

function parseSseDataFrame(frame: string): ApiResult<RuntimeAgentStreamEvent> {
  // Called by `streamAgentRun` for each frame to parse `data:` payload JSON and
  // validate one runtime event; returns deterministic malformed_response on failure.
  const dataLines = frame
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("data:"));

  if (dataLines.length === 0) {
    return malformedResponse("SSE frame missing data payload.");
  }

  const payload = dataLines.map((line) => line.slice(5).trim()).join("\n");

  try {
    const parsed: unknown = JSON.parse(payload);
    if (!isRuntimeAgentStreamEvent(parsed)) {
      return malformedResponse("Stream event payload did not match expected shape.");
    }

    return { ok: true, data: parsed };
  } catch {
    return malformedResponse("Stream event payload was not valid JSON.");
  }
}

function malformedResponse(message: string): { ok: false; error: ApiError } {
  // Shared by stream parser helpers to normalize schema/ordering failures into one
  // non-retryable API error contract consumed by the frontend run flow.
  return {
    ok: false,
    error: {
      type: "malformed_response",
      message,
      retryable: false,
    },
  };
}
