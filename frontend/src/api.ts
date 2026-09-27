import type {
  AgentCapability,
  Artifact,
  ArtifactExport,
  ArtifactSummary,
  ClarificationEntry,
  Task,
  TaskEvent
} from "./types";

export const DEMO_RESET_PHRASE = "RESET DEMO DATA";

const taskStatuses: readonly string[] = [
  "PROPOSED", "AWAITING_CLARIFICATION", "AWAITING_APPROVAL", "APPROVED",
  "EXECUTING", "COMPLETED", "FAILED", "REJECTED"
];

type Parser<T> = (value: unknown) => T | null;

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
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

function isClarification(value: unknown): value is ClarificationEntry {
  return isRecord(value) && typeof value.question === "string" && isNullableString(value.answer ?? null);
}

export const parseTask: Parser<Task> = (value) => {
  if (!(isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.message === "string" &&
    typeof value.status === "string" &&
    taskStatuses.includes(value.status) &&
    isNullableString(value.agent ?? null) &&
    isNullableString(value.skill ?? null) &&
    isNullableString(value.result ?? null) &&
    Array.isArray(value.events) &&
    value.events.every(isTaskEvent))) {
    return null;
  }
  const proposal = value.proposal ?? null;
  if (proposal !== null && !(isRecord(proposal) && typeof proposal.tool === "string" && typeof proposal.summary === "string")) {
    return null;
  }
  const history = value.clarification_history ?? [];
  const artifactIds = value.artifact_ids ?? [];
  if (!Array.isArray(history) || !history.every(isClarification) || !isStringArray(artifactIds)) {
    return null;
  }
  return {
    id: value.id,
    message: value.message,
    status: value.status as Task["status"],
    agent: (value.agent ?? null) as string | null,
    skill: (value.skill ?? null) as string | null,
    result: (value.result ?? null) as string | null,
    events: value.events,
    proposal: proposal as Task["proposal"],
    clarification_history: history.map((entry) => ({ question: entry.question, answer: entry.answer ?? null })),
    artifact_ids: artifactIds
  };
};

function parseMetadata(value: unknown): Record<string, string> | null {
  if (value === undefined || value === null) return {};
  if (!isRecord(value)) return null;
  const out: Record<string, string> = {};
  for (const [key, item] of Object.entries(value)) {
    out[key] = typeof item === "string" ? item : JSON.stringify(item);
  }
  return out;
}

const parseArtifactSummary: Parser<ArtifactSummary> = (value) => {
  if (!(isRecord(value) &&
    typeof value.id === "string" &&
    typeof value.task_id === "string" &&
    typeof value.agent === "string" &&
    typeof value.artifact_type === "string" &&
    typeof value.title === "string" &&
    typeof value.created_at === "string" &&
    typeof value.updated_at === "string" &&
    typeof value.status === "string")) {
    return null;
  }
  const metadata = parseMetadata(value.metadata);
  if (!metadata) return null;
  return {
    id: value.id,
    task_id: value.task_id,
    agent: value.agent,
    artifact_type: value.artifact_type,
    title: value.title,
    created_at: value.created_at,
    updated_at: value.updated_at,
    status: value.status,
    metadata
  };
};

const parseArtifact: Parser<Artifact> = (value) => {
  const summary = parseArtifactSummary(value);
  if (!summary || !isRecord(value) || typeof value.content !== "string") return null;
  return { ...summary, content: value.content };
};

const parseCapability: Parser<AgentCapability> = (value) => {
  if (!(isRecord(value) &&
    typeof value.name === "string" &&
    typeof value.description === "string" &&
    isStringArray(value.responsibilities) &&
    isStringArray(value.allowed_tools) &&
    isStringArray(value.allowed_skills) &&
    typeof value.memory_namespace === "string")) {
    return null;
  }
  const prohibited = value.prohibited_capabilities;
  return {
    name: value.name,
    description: value.description,
    responsibilities: value.responsibilities,
    allowed_tools: value.allowed_tools,
    allowed_skills: value.allowed_skills,
    memory_namespace: value.memory_namespace,
    prohibited_capabilities: isStringArray(prohibited) ? prohibited : undefined
  };
};

function listOf<T>(parser: Parser<T>): Parser<T[]> {
  return (value) => {
    if (!Array.isArray(value)) return null;
    const out: T[] = [];
    for (const item of value) {
      const parsed = parser(item);
      if (parsed === null) return null;
      out.push(parsed);
    }
    return out;
  };
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

async function send(path: string, init?: RequestInit): Promise<Response> {
  let response: Response;
  try {
    response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...init
    });
  } catch {
    throw new ApiError("Unable to reach the ZANE API. Is the backend running?", 0);
  }
  if (!response.ok) {
    const raw = await response.text();
    let payload: unknown = raw;
    try {
      payload = raw.trim() === "" ? null : (JSON.parse(raw) as unknown);
    } catch {
      payload = raw;
    }
    throw new ApiError(extractDetail(payload, `Request failed with status ${response.status}`), response.status);
  }
  return response;
}

async function request<T>(path: string, parser: Parser<T>, label: string, init?: RequestInit): Promise<T> {
  const response = await send(path, init);
  const raw = await response.text();
  let payload: unknown = null;
  if (raw.trim() !== "") {
    try {
      payload = JSON.parse(raw) as unknown;
    } catch {
      payload = raw;
    }
  }
  const parsed = parser(payload);
  if (parsed === null) {
    throw new ApiError(`The ZANE API returned an invalid ${label} response.`, response.status);
  }
  return parsed;
}

const taskPath = (id: string) => `/api/tasks/${encodeURIComponent(id)}`;
const artifactPath = (id: string) => `/api/artifacts/${encodeURIComponent(id)}`;

export function createTask(message: string): Promise<Task> {
  return request("/api/tasks", parseTask, "task", { method: "POST", body: JSON.stringify({ message }) });
}

export function getTask(id: string): Promise<Task> {
  return request(taskPath(id), parseTask, "task");
}

export function submitDecision(id: string, approved: boolean): Promise<Task> {
  return request(`${taskPath(id)}/decision`, parseTask, "task", {
    method: "POST",
    body: JSON.stringify({ approved })
  });
}

export function submitClarification(id: string, answer: string): Promise<Task> {
  return request(`${taskPath(id)}/clarify`, parseTask, "task", {
    method: "POST",
    body: JSON.stringify({ answer })
  });
}

export function listArtifacts(): Promise<ArtifactSummary[]> {
  return request("/api/artifacts", listOf(parseArtifactSummary), "artifact list");
}

export function getArtifact(id: string): Promise<Artifact> {
  return request(artifactPath(id), parseArtifact, "artifact");
}

function filenameFrom(disposition: string | null, fallback: string): string {
  if (disposition) {
    const encoded = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
    if (encoded) {
      try {
        return decodeURIComponent(encoded[1].trim());
      } catch {
        /* fall through to plain filename */
      }
    }
    const plain = /filename="?([^";]+)"?/i.exec(disposition);
    if (plain) return plain[1].trim();
  }
  return fallback;
}

export async function exportArtifact(id: string): Promise<ArtifactExport> {
  const response = await send(`${artifactPath(id)}/export`, { headers: { Accept: "text/markdown" } });
  const blob = await response.blob();
  const filename = filenameFrom(response.headers.get("Content-Disposition"), `zane-artifact-${id}.md`);
  return { filename: filename.toLowerCase().endsWith(".md") ? filename : `${filename}.md`, blob };
}

export function getCapabilities(): Promise<AgentCapability[]> {
  return request("/api/capabilities", listOf(parseCapability), "capabilities");
}

export function resetDemo(): Promise<{ status: "reset" }> {
  return request(
    "/api/demo/reset",
    (value) => (isRecord(value) && value.status === "reset" ? { status: "reset" as const } : null),
    "demo reset",
    { method: "POST", body: JSON.stringify({ confirmation: DEMO_RESET_PHRASE }) }
  );
}
