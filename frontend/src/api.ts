import type { Task, TaskEvent } from "./types";

const taskStatuses: readonly string[] = [
  "PROPOSED", "AWAITING_APPROVAL", "APPROVED", "EXECUTING", "COMPLETED", "FAILED", "REJECTED"
];

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isTaskEvent(value: unknown): value is TaskEvent {
  return isRecord(value) &&
    typeof value.timestamp === "string" &&
    typeof value.task_id === "string" &&
    isNullableString(value.agent) &&
    typeof value.event_type === "string" &&
    isNullableString(value.tool) &&
    isNullableString(value.skill) &&
    typeof value.status === "string" &&
    typeof value.summary === "string";
}

function isTask(value: unknown): value is Task {
  return isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.message === "string" &&
    typeof value.status === "string" &&
    taskStatuses.includes(value.status) &&
    isNullableString(value.agent) &&
    isNullableString(value.skill) &&
    isNullableString(value.result) &&
    Array.isArray(value.events) &&
    value.events.every(isTaskEvent) &&
    (value.proposal === null || (
      isRecord(value.proposal) &&
      typeof value.proposal.tool === "string" &&
      typeof value.proposal.summary === "string"
    ));
}

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function extractDetail(payload: unknown, fallback: string): string {
  if (typeof payload === "string" && payload.trim() !== "") {
    return payload;
  }
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : typeof item === "string"
              ? item
              : JSON.stringify(item)
        )
        .filter((msg) => msg.length > 0);
      if (messages.length > 0) {
        return messages.join("; ");
      }
    }
    if (detail != null) {
      return JSON.stringify(detail);
    }
  }
  return fallback;
}

async function request(path: string, init?: RequestInit): Promise<Task> {
  let response: Response;
  try {
    response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...init
    });
  } catch {
    throw new ApiError("Unable to reach the ZANE API. Is the backend running?", 0);
  }

  const raw = await response.text();
  let payload: unknown = null;
  if (raw.trim() !== "") {
    try {
      payload = JSON.parse(raw) as unknown;
    } catch {
      payload = raw;
    }
  }

  if (!response.ok) {
    throw new ApiError(
      extractDetail(payload, `Request failed with status ${response.status}`),
      response.status
    );
  }

  if (!isTask(payload)) {
    throw new ApiError("The ZANE API returned an invalid task response.", response.status);
  }
  return payload;
}

export function createTask(message: string): Promise<Task> {
  return request("/api/tasks", {
    method: "POST",
    body: JSON.stringify({ message })
  });
}

export function getTask(id: string): Promise<Task> {
  return request(`/api/tasks/${encodeURIComponent(id)}`);
}

export function submitDecision(id: string, approved: boolean): Promise<Task> {
  return request(`/api/tasks/${encodeURIComponent(id)}/decision`, {
    method: "POST",
    body: JSON.stringify({ approved })
  });
}
