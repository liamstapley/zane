import type { Task } from "../types";

interface Props {
  task: Task;
}

export default function ResultPanel({ task }: Props) {
  const failed = task.status === "FAILED";
  const rejected = task.status === "REJECTED";
  return (
    <section className={`panel ${failed ? "panel-failed" : "panel-result"}`}>
      <header className="panel-header">
        <h2>{failed ? "Error" : rejected ? "Outcome" : "Final result"}</h2>
      </header>
      <pre className="result-body">{task.result}</pre>
    </section>
  );
}
