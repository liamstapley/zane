import type { Proposal } from "../types";

interface Props {
  proposal: Proposal;
  agent: string | null;
  pending: boolean;
  onDecision: (approved: boolean) => void;
}

export default function ApprovalCard({ proposal, agent, pending, onDecision }: Props) {
  return (
    <section className="panel panel-approval">
      <header className="panel-header">
        <h2>Proposed mutation</h2>
        <span className="badge badge-warn">APPROVAL REQUIRED</span>
      </header>
      <p className="panel-sub">Nothing is changed until you approve. Rejecting leaves all data untouched.</p>
      <dl className="meta-grid">
        <div className="meta-item">
          <dt>Tool</dt>
          <dd className="mono">{proposal.tool}</dd>
        </div>
        <div className="meta-item">
          <dt>Requested by</dt>
          <dd>{agent ?? "Agent"}</dd>
        </div>
      </dl>
      <p className="approval-summary">{proposal.summary}</p>
      <div className="approval-actions">
        <button className="btn btn-primary" type="button" disabled={pending} onClick={() => onDecision(true)}>
          Approve
        </button>
        <button className="btn btn-ghost" type="button" disabled={pending} onClick={() => onDecision(false)}>
          Reject
        </button>
      </div>
    </section>
  );
}
