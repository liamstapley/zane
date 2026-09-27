import StatusBadge from "./StatusBadge";
import type { Task } from "../types";

interface Props {
  task: Task;
  restored: boolean;
  onNewTask: () => void;
  disabled: boolean;
}

export default function TaskSummary({ task, restored, onNewTask, disabled }: Props) {
  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Task</h2>
        <StatusBadge status={task.status} />
      </header>
      {restored && <p className="restored-note">Restored from your last session.</p>}
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
          <dt>Clarifications</dt>
          <dd>{task.clarification_history.length}</dd>
        </div>
        <div className="meta-item">
          <dt>Artifacts</dt>
          <dd>{task.artifact_ids.length}</dd>
        </div>
        <div className="meta-item meta-wide">
          <dt>Task ID</dt>
          <dd className="mono">{task.id}</dd>
        </div>
      </dl>
      <button type="button" className="btn btn-ghost btn-sm panel-action" onClick={onNewTask} disabled={disabled}>New task</button>
    </section>
  );
}
