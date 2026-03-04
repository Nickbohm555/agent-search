import { SubQueryToolAssignment } from "../utils/api";

export type RuntimeAgentStreamEventName =
  | "heartbeat"
  | "progress"
  | "sub_queries"
  | "tool_assignments"
  | "retrieval_result"
  | "validation_result"
  | "error"
  | "completed";

type RuntimeAgentStreamOtherEventName = Exclude<
  RuntimeAgentStreamEventName,
  "heartbeat" | "progress" | "sub_queries" | "tool_assignments" | "error" | "completed"
>;

export interface RuntimeAgentStreamEventBase {
  sequence: number;
  event: RuntimeAgentStreamEventName;
  data: unknown;
}

export interface RuntimeAgentStreamHeartbeatEvent extends RuntimeAgentStreamEventBase {
  event: "heartbeat";
  data: {
    status: string;
    query: string;
  };
}

export interface RuntimeAgentStreamProgressEvent extends RuntimeAgentStreamEventBase {
  event: "progress";
  data: {
    step: string;
    status: string;
  };
}

export interface RuntimeAgentStreamSubQueriesEvent extends RuntimeAgentStreamEventBase {
  event: "sub_queries";
  data: {
    sub_queries: string[];
    count: number;
  };
}

export interface RuntimeAgentStreamToolAssignmentsEvent extends RuntimeAgentStreamEventBase {
  event: "tool_assignments";
  data: {
    tool_assignments: SubQueryToolAssignment[];
    count: number;
  };
}

export interface RuntimeAgentStreamCompletedData {
  agent_name: string;
  output: string;
  thread_id: string;
  checkpoint_id?: string | null;
  sub_queries: string[];
  tool_assignments: SubQueryToolAssignment[];
}

export interface RuntimeAgentStreamCompletedEvent extends RuntimeAgentStreamEventBase {
  event: "completed";
  data: RuntimeAgentStreamCompletedData;
}

export interface RuntimeAgentStreamErrorEvent extends RuntimeAgentStreamEventBase {
  event: "error";
  data: {
    message: string;
    retryable?: boolean;
  };
}

export interface RuntimeAgentStreamOtherEvent extends RuntimeAgentStreamEventBase {
  event: RuntimeAgentStreamOtherEventName;
  data: Record<string, unknown>;
}

export type RuntimeAgentStreamEvent =
  | RuntimeAgentStreamHeartbeatEvent
  | RuntimeAgentStreamProgressEvent
  | RuntimeAgentStreamSubQueriesEvent
  | RuntimeAgentStreamToolAssignmentsEvent
  | RuntimeAgentStreamErrorEvent
  | RuntimeAgentStreamCompletedEvent
  | RuntimeAgentStreamOtherEvent;

const STREAM_EVENT_NAMES: ReadonlySet<string> = new Set([
  "heartbeat",
  "progress",
  "sub_queries",
  "tool_assignments",
  "retrieval_result",
  "validation_result",
  "error",
  "completed",
]);

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isToolAssignment(value: unknown): value is SubQueryToolAssignment {
  if (!isObject(value)) {
    return false;
  }

  return (
    typeof value.sub_query === "string" &&
    (value.tool === "internal" || value.tool === "web")
  );
}

export function isRuntimeAgentStreamEventName(value: unknown): value is RuntimeAgentStreamEventName {
  return typeof value === "string" && STREAM_EVENT_NAMES.has(value);
}

export function isRuntimeAgentStreamCompletedData(value: unknown): value is RuntimeAgentStreamCompletedData {
  if (!isObject(value)) {
    return false;
  }

  return (
    typeof value.agent_name === "string" &&
    value.agent_name.trim().length > 0 &&
    typeof value.output === "string" &&
    typeof value.thread_id === "string" &&
    value.thread_id.trim().length > 0 &&
    (value.checkpoint_id === undefined ||
      value.checkpoint_id === null ||
      typeof value.checkpoint_id === "string") &&
    isStringArray(value.sub_queries) &&
    Array.isArray(value.tool_assignments) &&
    value.tool_assignments.every(isToolAssignment)
  );
}

export function isRuntimeAgentStreamEvent(value: unknown): value is RuntimeAgentStreamEvent {
  if (!isObject(value)) {
    return false;
  }

  if (
    typeof value.sequence !== "number" ||
    !Number.isInteger(value.sequence) ||
    value.sequence < 1 ||
    !isRuntimeAgentStreamEventName(value.event) ||
    !isObject(value.data)
  ) {
    return false;
  }

  if (value.event === "heartbeat") {
    return typeof value.data.status === "string" && typeof value.data.query === "string";
  }

  if (value.event === "progress") {
    return typeof value.data.step === "string" && typeof value.data.status === "string";
  }

  if (value.event === "sub_queries") {
    return isStringArray(value.data.sub_queries) && typeof value.data.count === "number";
  }

  if (value.event === "tool_assignments") {
    return (
      Array.isArray(value.data.tool_assignments) &&
      value.data.tool_assignments.every(isToolAssignment) &&
      typeof value.data.count === "number"
    );
  }

  if (value.event === "completed") {
    return isRuntimeAgentStreamCompletedData(value.data);
  }

  if (value.event === "error") {
    return (
      typeof value.data.message === "string" &&
      value.data.message.trim().length > 0 &&
      (value.data.retryable === undefined || typeof value.data.retryable === "boolean")
    );
  }

  return true;
}
