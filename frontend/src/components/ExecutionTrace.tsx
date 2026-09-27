import type { TaskEvent } from "../types";

interface Props {
  events: TaskEvent[];
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

export default function ExecutionTrace({ events }: Props) {
  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Execution trace</h2>
        <span className="count">{events.length} events</span>
      </header>
      {events.length === 0 ? (
        <p className="empty">No execution events recorded yet.</p>
      ) : (
        <ol className="trace">
          {events.map((event, index) => (
            <li className="trace-item" key={`${event.task_id}-${index}-${event.event_type}`}>
              <div className="trace-head">
                <span className="trace-type">{event.event_type.replace(/_/g, " ")}</span>
                <time className="trace-time">{formatTimestamp(event.timestamp)}</time>
              </div>
              {event.summary ? <p className="trace-summary">{event.summary}</p> : null}
              <div className="tag-row">
                {event.agent ? <span className="tag">agent: {event.agent}</span> : null}
                {event.skill ? <span className="tag">skill: {event.skill}</span> : null}
                {event.tool ? <span className="tag tag-tool">tool: {event.tool}</span> : null}
                {event.status ? <span className="tag">status: {event.status}</span> : null}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
