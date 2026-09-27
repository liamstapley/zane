import { useState, type FormEvent } from "react";
import { DEMO_RESET_PHRASE, resetDemo } from "../api";
import Modal from "./Modal";

interface Props {
  onClose: () => void;
  onReset: () => void;
}

export default function DemoResetModal({ onClose, onReset }: Props) {
  const [typed, setTyped] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const matches = typed === DEMO_RESET_PHRASE;

  async function submit(event?: FormEvent) {
    event?.preventDefault();
    if (!matches || pending) return;
    setPending(true);
    setError(null);
    try {
      await resetDemo();
      onReset();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Reset failed.");
      setPending(false);
    }
  }

  return (
    <Modal
      title="Reset demo data?"
      onClose={onClose}
      dismissible={!pending}
      footer={
        <>
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={pending}>Cancel</button>
          <button type="button" className="btn btn-danger" onClick={() => void submit()} disabled={!matches || pending}>
            {pending ? "Resetting..." : "Reset demo data"}
          </button>
        </>
      }
    >
      <form onSubmit={submit} className="reset-form">
        <p className="task-message">
          This restores the local mock data to its original state and clears saved tasks and artifacts. It cannot be undone.
        </p>
        <label htmlFor="reset-confirm" className="label">
          Type <strong className="mono reset-phrase">{DEMO_RESET_PHRASE}</strong> to confirm
        </label>
        <input
          id="reset-confirm"
          className="text-input mono"
          value={typed}
          autoComplete="off"
          spellCheck={false}
          disabled={pending}
          onChange={(event) => setTyped(event.target.value)}
        />
        {error && <div className="error-inline" role="alert">{error}</div>}
      </form>
    </Modal>
  );
}
