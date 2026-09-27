import { useState } from "react";
import { createTask, getTask, submitDecision } from "./api";
import ApprovalCard from "./components/ApprovalCard";
import ChatInput from "./components/ChatInput";
import ExecutionTrace from "./components/ExecutionTrace";
import ResultPanel from "./components/ResultPanel";
import StatusBadge from "./components/StatusBadge";
import TaskSummary from "./components/TaskSummary";
import type { Task } from "./types";

export default function App() {
  const [task, setTask] = useState<Task | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(message: string) {
    setBusy(true);
    setError(null);
    try {
      setTask(await createTask(message));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Task request failed.");
    } finally {
      setBusy(false);
    }
  }

  async function decide(approved: boolean) {
    if (!task) return;
    setBusy(true);
    setError(null);
    try {
      setTask(await submitDecision(task.id, approved));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Approval request failed.");
      try {
        setTask(await getTask(task.id));
      } catch (refreshError) {
        const detail = refreshError instanceof Error ? refreshError.message : "Unable to refresh the task.";
        setError(`Approval request failed, and task refresh failed: ${detail}`);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">Z</span><div><strong>ZANE</strong><small>Local agent workspace</small></div></div>
        <span className="topbar-note">Isolated agents | Human-approved changes</span>
      </header>

      <main className="layout">
        <section className="workspace" aria-label="Chat">
          <div className="section-heading">
            <div><span className="eyebrow">WORKSPACE</span><h1>What can I help with?</h1></div>
            <span className="agent-indicator">Agent: <strong>{task?.agent ?? "Not selected"}</strong></span>
          </div>
          <div className="conversation">
            {task ? (
              <>
                <div className="chat-bubble user-bubble"><span className="bubble-label">You</span><p>{task.message}</p></div>
                {task.result && <div className="chat-bubble assistant-bubble"><span className="bubble-label">ZANE · {task.agent ?? "Orchestrator"}</span><p>{task.result}</p></div>}
                {task.status === "AWAITING_APPROVAL" && <div className="chat-note">This operation is paused until you approve or reject it.</div>}
              </>
            ) : (
              <div className="welcome"><span className="welcome-icon">Z</span><h2>One task, the right agent.</h2>
                <p>Ask for a HenHacks sponsorship update or a CS+Social Good meeting agenda. Changes wait for your approval.</p>
                <div className="suggestions"><span>Try: Summarize HenHacks sponsorship status</span><span>Prepare a CS+Social Good meeting agenda</span></div>
              </div>
            )}
          </div>
          {error && <div className="error-banner" role="alert">{error}</div>}
          <ChatInput disabled={busy} onSubmit={send} />
        </section>

        <aside className="sidebar" aria-label="Task activity">
          {task ? (
            <>
              <TaskSummary task={task} />
              {task.proposal && task.status === "AWAITING_APPROVAL" && <ApprovalCard proposal={task.proposal} pending={busy} onDecision={decide} />}
              {task.result && task.status !== "AWAITING_APPROVAL" && <ResultPanel task={task} />}
              <ExecutionTrace events={task.events} />
            </>
          ) : (
            <>
              <section className="panel"><header className="panel-header"><h2>Task status</h2><StatusBadge status="PROPOSED" /></header><p className="empty">Your task activity will appear here.</p></section>
              <ExecutionTrace events={[]} />
            </>
          )}
        </aside>
      </main>
    </div>
  );
}
