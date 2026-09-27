import type { ClarificationEntry } from "../types";

interface Props {
  history: ClarificationEntry[];
  awaiting: boolean;
}

export default function ClarificationCard({ history, awaiting }: Props) {
  if (history.length === 0 && !awaiting) return null;
  return (
    <section className={`panel ${awaiting ? "panel-approval" : ""}`}>
      <header className="panel-header">
        <h2>Clarifications</h2>
        {awaiting ? <span className="badge badge-warn">NEEDS YOUR ANSWER</span> : <span className="count">{history.length} answered</span>}
      </header>
      <ol className="clarify-list">
        {history.map((entry, index) => (
          <li key={`${index}-${entry.question}`} className="clarify-item">
            <p className="clarify-q"><span className="label">Question</span>{entry.question}</p>
            {entry.answer !== null
              ? <p className="clarify-a"><span className="label">Your answer</span>{entry.answer}</p>
              : <p className="clarify-pending">Waiting for your answer in the composer.</p>}
          </li>
        ))}
      </ol>
    </section>
  );
}
