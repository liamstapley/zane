import StatusBadge from "./StatusBadge";
import type { Task } from "../types";

interface Props {
  task: Task;
}

export default function TaskSummary({ task }: Props) {
  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Task</h2>
        <StatusBadge status={task.status} />
      </header>
      <p className="task-message">{task.message}</p>
      <dl className="meta-grid">
        <div className="meta-item">
          <dt>Agent</dt>
          <dd>{task.agent ?? "Not selected"}</dd>
        </div>
        <div className="meta-item">
          <dt>Skill</dt>
          <dd>{task.skill ?? "None active"}</dd>
        </div>
        <div className="meta-item">
          <dt>Task ID</dt>
          <dd className="mono">{task.id}</dd>
        </div>
      </dl>
    </section>
  );
}
