import type { TaskStatus } from "../types";

interface Props {
  status: TaskStatus;
}

function toneFor(status: TaskStatus): string {
  const normalized = status.toUpperCase();
  if (normalized === "COMPLETED") return "ok";
  if (normalized === "FAILED" || normalized === "REJECTED") return "bad";
  if (normalized === "AWAITING_APPROVAL") return "warn";
  if (normalized === "PROPOSED" || normalized === "APPROVED" || normalized === "EXECUTING") return "busy";
  return "neutral";
}

export default function StatusBadge({ status }: Props) {
  return <span className={`badge badge-${toneFor(status)}`}>{status.replace(/_/g, " ")}</span>;
}
