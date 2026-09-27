import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, createTask, getTask, listArtifacts, submitClarification, submitDecision } from "./api";
import ApprovalCard from "./components/ApprovalCard";
import ArtifactPanel from "./components/ArtifactPanel";
import CapabilityViewer from "./components/CapabilityViewer";
import ChatInput from "./components/ChatInput";
import ClarificationCard from "./components/ClarificationCard";
import DemoResetModal from "./components/DemoResetModal";
import ExamplePrompts from "./components/ExamplePrompts";
import ExecutionTrace from "./components/ExecutionTrace";
import ResultPanel from "./components/ResultPanel";
import TaskSummary from "./components/TaskSummary";
import type { ArtifactSummary, Task } from "./types";

const LAST_TASK_KEY = "zane:lastTaskId";

function readStoredTaskId(): string | null {
  try {
    return window.localStorage.getItem(LAST_TASK_KEY);
  } catch {
    return null;
  }
}

function storeTaskId(id: string | null) {
  try {
    if (id) window.localStorage.setItem(LAST_TASK_KEY, id);
    else window.localStorage.removeItem(LAST_TASK_KEY);
  } catch {
    /* storage unavailable (private mode); persistence is best-effort */
  }
}

function messageOf(cause: unknown, fallback: string): string {
  return cause instanceof Error ? cause.message : fallback;
}

export default function App() {
  const [task, setTaskState] = useState<Task | null>(null);
  const [busy, setBusy] = useState(false);
  const [restoring, setRestoring] = useState(() => readStoredTaskId() !== null);
  const [restored, setRestored] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [startNew, setStartNew] = useState(false);
  const [artifacts, setArtifacts] = useState<ArtifactSummary[]>([]);
  const [artifactsLoading, setArtifactsLoading] = useState(false);
  const [artifactsError, setArtifactsError] = useState<string | null>(null);
  const [showCapabilities, setShowCapabilities] = useState(false);
  const [showReset, setShowReset] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const artifactRequest = useRef(0);

  const setTask = useCallback((next: Task | null) => {
    setTaskState(next);
    storeTaskId(next?.id ?? null);
  }, []);

  const refreshArtifacts = useCallback(async () => {
    const requestId = ++artifactRequest.current;
    setArtifactsLoading(true);
    setArtifactsError(null);
    try {
      const list = await listArtifacts();
      if (requestId === artifactRequest.current) setArtifacts(list);
    } catch (cause) {
      if (requestId === artifactRequest.current) setArtifactsError(messageOf(cause, "Unable to load artifacts."));
    } finally {
      if (requestId === artifactRequest.current) setArtifactsLoading(false);
    }
  }, []);

  useEffect(() => {
    const storedId = readStoredTaskId();
    if (!storedId) return;
    let cancelled = false;
    getTask(storedId)
      .then((value) => {
        if (cancelled) return;
        setTaskState(value);
        setRestored(true);
      })
      .catch((cause: unknown) => {
        if (cancelled) return;
        if (cause instanceof ApiError && cause.status === 404) {
          storeTaskId(null);
        } else {
          setError(`Could not restore your last task: ${messageOf(cause, "unknown error")}`);
        }
      })
      .finally(() => { if (!cancelled) setRestoring(false); });
    return () => { cancelled = true; };
  }, []);

  const artifactKey = task ? `${task.id}|${task.status}|${task.artifact_ids.join(",")}` : "none";
  useEffect(() => {
    void refreshArtifacts();
  }, [artifactKey, refreshArtifacts]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 3500);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const clarifying = task?.status === "AWAITING_CLARIFICATION" && !startNew;

  async function recover(taskId: string, prefix: string, cause: unknown) {
    setError(`${prefix}: ${messageOf(cause, "request failed")}`);
    try {
      setTask(await getTask(taskId));
    } catch (refreshError) {
      setError(`${prefix}, and task refresh failed: ${messageOf(refreshError, "unknown error")}`);
    }
  }

  async function submit(message: string) {
    setBusy(true);
    setError(null);
    setRestored(false);
    try {
      if (clarifying && task) {
        const taskId = task.id;
        try {
          setTask(await submitClarification(taskId, message));
          setDraft("");
        } catch (cause) {
          await recover(taskId, "Clarification failed", cause);
        }
      } else {
        setTask(await createTask(message));
        setStartNew(false);
        setDraft("");
      }
    } catch (cause) {
      setError(messageOf(cause, "Task request failed."));
    } finally {
      setBusy(false);
    }
  }

  async function decide(approved: boolean) {
    if (!task) return;
    const taskId = task.id;
    setBusy(true);
    setError(null);
    setRestored(false);
    try {
      setTask(await submitDecision(taskId, approved));
    } catch (cause) {
      await recover(taskId, "Approval request failed", cause);
    } finally {
      setBusy(false);
    }
  }

  function pickExample(prompt: string) {
    setDraft(prompt);
    if (task?.status === "AWAITING_CLARIFICATION") setStartNew(true);
    window.requestAnimationFrame(() => inputRef.current?.focus());
  }

  function newTask() {
    setTask(null);
    setRestored(false);
    setStartNew(false);
    setError(null);
    setDraft("");
    window.requestAnimationFrame(() => inputRef.current?.focus());
  }

  function handleReset() {
    setShowReset(false);
    newTask();
    setArtifacts([]);
    void refreshArtifacts();
    setNotice("Demo data reset to its original state.");
  }

  const questions = new Set(task?.clarification_history.map((entry) => entry.question.trim()) ?? []);
  const showResultBubble = Boolean(task?.result) && !(task?.status === "AWAITING_CLARIFICATION" && questions.has((task?.result ?? "").trim()));

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">Z</span><div><strong>ZANE</strong><small>Local agent workspace</small></div></div>
        <div className="topbar-actions">
          <span className="demo-indicator" title="ZANE is running against local mock data. No real emails, trackers or Discord messages are touched.">
            <span className="demo-dot" aria-hidden="true" />Demo mode &middot; mock data
          </span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowCapabilities(true)}>Agents</button>
          <button type="button" className="btn btn-outline-danger btn-sm" onClick={() => setShowReset(true)} disabled={busy}>Reset demo</button>
        </div>
      </header>

      {notice && <div className="toast" role="status">{notice}</div>}

      <main className="layout">
        <section className="workspace" aria-label="Chat">
          <div className="section-heading">
            <div><span className="eyebrow">WORKSPACE</span><h1>What can I help with?</h1></div>
            <button type="button" className="agent-indicator" onClick={() => setShowCapabilities(true)} title="View agent capabilities">
              Agent: <strong>{task?.agent ?? "Not selected"}</strong>
            </button>
          </div>
          <div className="conversation" aria-live="polite">
            {restoring && !task ? (
              <div className="welcome"><span className="welcome-icon spinner" aria-hidden="true" /><p>Restoring your last task...</p></div>
            ) : task ? (
              <>
                <div className="chat-bubble user-bubble"><span className="bubble-label">You</span><p>{task.message}</p></div>
                {task.clarification_history.map((entry, index) => (
                  <div className="chat-pair" key={`${index}-${entry.question}`}>
                    <div className="chat-bubble assistant-bubble clarify-bubble">
                      <span className="bubble-label">ZANE &middot; {task.agent ?? "Orchestrator"} asks</span><p>{entry.question}</p>
                    </div>
                    {entry.answer !== null && <div className="chat-bubble user-bubble"><span className="bubble-label">You</span><p>{entry.answer}</p></div>}
                  </div>
                ))}
                {showResultBubble && (
                  <div className={`chat-bubble assistant-bubble ${task.status === "FAILED" ? "error-bubble" : ""}`}>
                    <span className="bubble-label">ZANE &middot; {task.agent ?? "Orchestrator"}</span><p>{task.result}</p>
                  </div>
                )}
                {task.status === "AWAITING_CLARIFICATION" && <div className="chat-note">ZANE needs one more detail. Answer below to resume task <span className="mono">{task.id}</span>.</div>}
                {task.status === "AWAITING_APPROVAL" && <div className="chat-note">A proposed change is paused until you approve or reject it.</div>}
                {task.status === "REJECTED" && <div className="chat-note muted">Proposal rejected. No changes were made.</div>}
                {!busy && ["COMPLETED", "FAILED", "REJECTED"].includes(task.status) && (
                  <div className="followup">
                    <span className="hint">Try another example:</span>
                    <ExamplePrompts disabled={busy} onPick={pickExample} compact />
                  </div>
                )}
                {busy && <div className="chat-note muted"><span className="spinner inline" aria-hidden="true" /> ZANE is working...</div>}
              </>
            ) : (
              <div className="welcome"><span className="welcome-icon">Z</span><h2>One task, the right agent.</h2>
                <p>Pick an example or describe your own task. Any change to data waits for your approval.</p>
                <ExamplePrompts disabled={busy} onPick={pickExample} />
              </div>
            )}
          </div>
          {error && <div className="error-banner" role="alert"><span>{error}</span><button type="button" className="icon-btn" aria-label="Dismiss error" onClick={() => setError(null)}>&times;</button></div>}
          <ChatInput
            ref={inputRef}
            value={draft}
            onChange={setDraft}
            disabled={busy || restoring}
            mode={clarifying ? "clarify" : "task"}
            onSubmit={submit}
            onCancelClarify={() => { setStartNew(true); setDraft(""); }}
          />
        </section>

        <aside className="sidebar" aria-label="Task activity">
          {task ? (
            <>
              <TaskSummary task={task} restored={restored} onNewTask={newTask} disabled={busy} />
              <ClarificationCard history={task.clarification_history} awaiting={task.status === "AWAITING_CLARIFICATION"} />
              {task.proposal && task.status === "AWAITING_APPROVAL" && <ApprovalCard proposal={task.proposal} agent={task.agent} pending={busy} onDecision={decide} />}
              {task.result && !["AWAITING_APPROVAL", "AWAITING_CLARIFICATION"].includes(task.status) && <ResultPanel task={task} />}
            </>
          ) : (
            <section className="panel"><header className="panel-header"><h2>Task status</h2><span className="badge">IDLE</span></header><p className="empty">{restoring ? "Restoring your last task..." : "Your task activity will appear here."}</p></section>
          )}
          <ArtifactPanel
            artifacts={artifacts}
            loading={artifactsLoading}
            error={artifactsError}
            taskArtifactIds={task?.artifact_ids ?? []}
            hasTask={task !== null}
            onRefresh={() => void refreshArtifacts()}
          />
          <ExecutionTrace events={task?.events ?? []} />
        </aside>
      </main>

      {showCapabilities && <CapabilityViewer activeAgent={task?.agent ?? null} onClose={() => setShowCapabilities(false)} />}
      {showReset && <DemoResetModal onClose={() => setShowReset(false)} onReset={handleReset} />}
    </div>
  );
}
