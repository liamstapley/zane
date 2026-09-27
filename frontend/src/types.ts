export type TaskStatus =
  | "PROPOSED"
  | "AWAITING_CLARIFICATION"
  | "AWAITING_APPROVAL"
  | "APPROVED"
  | "EXECUTING"
  | "COMPLETED"
  | "FAILED"
  | "REJECTED";

export interface TaskEvent {
  timestamp: string;
  task_id: string;
  agent: string | null;
  event_type: string;
  tool: string | null;
  skill: string | null;
  status: string;
  summary: string;
}

export interface Proposal {
  tool: string;
  summary: string;
}

export interface ClarificationEntry {
  question: string;
  answer: string | null;
}

export interface Task {
  id: string;
  message: string;
  status: TaskStatus;
  agent: string | null;
  skill: string | null;
  result: string | null;
  events: TaskEvent[];
  proposal: Proposal | null;
  clarification_history: ClarificationEntry[];
  artifact_ids: string[];
}

export interface ArtifactSummary {
  id: string;
  task_id: string;
  agent: string;
  artifact_type: string;
  title: string;
  created_at: string;
  updated_at: string;
  status: string;
  metadata: Record<string, string>;
}

export interface Artifact extends ArtifactSummary {
  content: string;
}

export interface ArtifactExport {
  filename: string;
  blob: Blob;
}

export interface AgentCapability {
  name: string;
  description: string;
  responsibilities: string[];
  allowed_tools: string[];
  allowed_skills: string[];
  memory_namespace: string;
  prohibited_capabilities?: string[];
}
