export type TaskStatus =
  | "PROPOSED"
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

export interface Task {
  id: string;
  message: string;
  status: TaskStatus;
  agent: string | null;
  skill: string | null;
  result: string | null;
  events: TaskEvent[];
  proposal: Proposal | null;
}
