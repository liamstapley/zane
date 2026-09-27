import type { Proposal } from "../types";

interface Props {
  proposal: Proposal;
  pending: boolean;
  onDecision: (approved: boolean) => void;
}

export default function ApprovalCard({ proposal, pending, onDecision }: Props) {
  return (
    <section className="panel panel-approval">
      <header className="panel-header">
        <h2>Approval required</h2>
        <span className="badge badge-warn">ACTION PENDING</span>
      </header>
      <p className="approval-tool">
        <span className="label">Tool</span>
        <span className="mono">{proposal.tool}</span>
      </p>
      <p className="approval-summary">{proposal.summary}</p>
      <div className="approval-actions">
        <button
          className="btn btn-primary"
          type="button"
          disabled={pending}
          onClick={() => onDecision(true)}
        >
          Approve
        </button>
        <button
          className="btn btn-ghost"
          type="button"
          disabled={pending}
          onClick={() => onDecision(false)}
        >
          Reject
        </button>
      </div>
    </section>
  );
}
