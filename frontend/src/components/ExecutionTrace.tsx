import { useMemo, useState } from "react";
import type { TaskEvent } from "../types";

export type TraceCategory =
  | "lifecycle"
  | "routing"
  | "skill"
  | "clarification"
  | "mutation"
  | "decision"
  | "tool"
  | "artifact"
  | "error"
  | "other";

const CATEGORY_LABELS: Record<TraceCategory, string> = {
  lifecycle: "Lifecycle",
  routing: "Routing",
  skill: "Skill",
  clarification: "Clarification",
  mutation: "Proposed mutation",
  decision: "Decision",
  tool: "Tool",
  artifact: "Artifact",
  error: "Error",
  other: "Other"
};

export function categorize(eventType: string): TraceCategory {
  const type = eventType.toLowerCase();
  if (type.includes("fail") || type.includes("error")) return "error";
  if (type.includes("clarif")) return "clarification";
  if (type === "approval_requested" || type.includes("mutation") || type.includes("proposal") || type.includes("proposed")) return "mutation";
  if (type.includes("approval") || type.includes("decision") || type.includes("reject") || type.includes("approved")) return "decision";
  if (type.includes("artifact")) return "artifact";
  if (type.startsWith("tool") || type.includes("_tool")) return "tool";
  if (type.includes("skill")) return "skill";
  if (type.includes("rout") || type.includes("agent_selected") || type.includes("delegat") || type.includes("handoff")) return "routing";
  if (type.startsWith("task") || type.includes("status")) return "lifecycle";
  return "other";
}

const HEADLINES: Record<string, string> = {
  task_created: "Task received",
  task_status: "Status update",
  task_completed: "Task completed",
  task_failed: "Task failed",
  skill_loaded: "Skill loaded",
  approval_requested: "Mutation proposed - awaiting approval",
  approval_granted: "Mutation approved",
  approval_rejected: "Mutation rejected",
  tool_call: "Tool invoked",
  tool_result: "Tool result",
  clarification: "Clarification requested"
};

function headline(eventType: string): string {
  const fallback = eventType.replace(/_/g, " ");
  return HEADLINES[eventType] ?? fallback.charAt(0).toUpperCase() + fallback.slice(1);
}

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "--:--:--";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleTimeString();
}

interface Props {
  events: TaskEvent[];
}

export default function ExecutionTrace({ events }: Props) {
  const [filter, setFilter] = useState<TraceCategory | "all">("all");

  const categorized = useMemo(
    () => events.map((event, index) => ({ event, index, category: categorize(event.event_type) })),
    [events]
  );
  const counts = useMemo(() => {
    const map = new Map<TraceCategory, number>();
    for (const item of categorized) map.set(item.category, (map.get(item.category) ?? 0) + 1);
    return map;
  }, [categorized]);

  const activeFilter = filter !== "all" && !counts.has(filter) ? "all" : filter;
  const visible = activeFilter === "all" ? categorized : categorized.filter((item) => item.category === activeFilter);

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Execution trace</h2>
        <span className="count">{events.length} events</span>
      </header>
      <p className="panel-sub">Safe, user-facing summaries of each step. Internal reasoning is never shown.</p>
      {events.length === 0 ? (
        <p className="empty">No execution events recorded yet.</p>
      ) : (
        <>
          <div className="trace-filters" role="group" aria-label="Filter trace by category">
            <button type="button" className={`filter-chip ${activeFilter === "all" ? "active" : ""}`} aria-pressed={activeFilter === "all"} onClick={() => setFilter("all")}>
              All <span>{events.length}</span>
            </button>
            {(Object.keys(CATEGORY_LABELS) as TraceCategory[]).filter((key) => counts.has(key)).map((key) => (
              <button
                type="button"
                key={key}
                className={`filter-chip cat-${key} ${activeFilter === key ? "active" : ""}`}
                aria-pressed={activeFilter === key}
                onClick={() => setFilter(key)}
              >
                {CATEGORY_LABELS[key]} <span>{counts.get(key)}</span>
              </button>
            ))}
          </div>
          <ol className="trace">
            {visible.map(({ event, index, category }) => (
              <li className={`trace-item cat-${category}`} key={`${event.task_id}-${index}-${event.event_type}`}>
                <div className="trace-head">
                  <span className="trace-type">
                    <span className={`cat-pill cat-${category}`}>{CATEGORY_LABELS[category]}</span>
                    {headline(event.event_type)}
                  </span>
                  <time className="trace-time" dateTime={event.timestamp}>{formatTimestamp(event.timestamp)}</time>
                </div>
                {event.summary ? <p className="trace-summary">{event.summary}</p> : null}
                <div className="tag-row">
                  {event.agent ? <span className="tag">agent: {event.agent}</span> : null}
                  {event.skill ? <span className="tag">skill: {event.skill}</span> : null}
                  {event.tool ? <span className="tag tag-tool">tool: {event.tool}</span> : null}
                  {event.status ? <span className="tag">status: {event.status.toLowerCase().replace(/_/g, " ")}</span> : null}
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}
