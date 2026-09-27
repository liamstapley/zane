import { useEffect, useState } from "react";
import { exportArtifact, getArtifact } from "../api";
import type { Artifact, ArtifactSummary } from "../types";
import Modal from "./Modal";

interface Props {
  artifacts: ArtifactSummary[];
  loading: boolean;
  error: string | null;
  taskArtifactIds: string[];
  hasTask: boolean;
  onRefresh: () => void;
}

function formatDate(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}

function humanize(value: string): string {
  return value.replace(/_/g, " ");
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function copyText(text: string): Promise<void> {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.appendChild(area);
  area.select();
  const ok = document.execCommand("copy");
  area.remove();
  if (!ok) throw new Error("Copy is not supported in this browser.");
}

function ArtifactDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setArtifact(null);
    setError(null);
    getArtifact(id)
      .then((value) => { if (!cancelled) setArtifact(value); })
      .catch((cause: unknown) => { if (!cancelled) setError(cause instanceof Error ? cause.message : "Unable to load artifact."); });
    return () => { cancelled = true; };
  }, [id]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 2200);
    return () => window.clearTimeout(timer);
  }, [notice]);

  async function copy() {
    if (!artifact) return;
    try {
      await copyText(`# ${artifact.title}\n\n${artifact.content}\n`);
      setNotice("Copied as Markdown.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Copy failed.");
    }
  }

  async function download() {
    setDownloading(true);
    setError(null);
    try {
      const { blob, filename } = await exportArtifact(id);
      triggerDownload(blob, filename);
      setNotice(`Downloaded ${filename}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Download failed.");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Modal
      title={artifact?.title ?? "Artifact"}
      onClose={onClose}
      wide
      footer={
        <>
          <span className="modal-notice" role="status">{notice}</span>
          <button type="button" className="btn btn-ghost" onClick={copy} disabled={!artifact}>Copy</button>
          <button type="button" className="btn btn-primary" onClick={download} disabled={!artifact || downloading}>
            {downloading ? "Preparing..." : "Download .md"}
          </button>
        </>
      }
    >
      {error && <div className="error-inline" role="alert">{error}</div>}
      {!artifact && !error && <p className="empty">Loading artifact...</p>}
      {artifact && (
        <>
          <div className="tag-row artifact-meta">
            <span className="tag tag-tool">{humanize(artifact.artifact_type)}</span>
            <span className="tag">agent: {artifact.agent}</span>
            <span className="tag">status: {artifact.status}</span>
            <span className="tag">updated {formatDate(artifact.updated_at)}</span>
            {Object.entries(artifact.metadata).map(([key, value]) => (
              <span className="tag" key={key}>{humanize(key)}: {value}</span>
            ))}
          </div>
          <p className="hint mono">Task {artifact.task_id} &middot; Artifact {artifact.id}</p>
          <pre className="artifact-content">{artifact.content}</pre>
        </>
      )}
    </Modal>
  );
}

export default function ArtifactPanel({ artifacts, loading, error, taskArtifactIds, hasTask, onRefresh }: Props) {
  const [scope, setScope] = useState<"task" | "all">(hasTask ? "task" : "all");
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    setScope(hasTask ? "task" : "all");
  }, [hasTask]);

  const taskIds = new Set(taskArtifactIds);
  const sorted = [...artifacts].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  const visible = scope === "task" ? sorted.filter((item) => taskIds.has(item.id)) : sorted;

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Artifacts</h2>
        <button type="button" className="link-btn" onClick={onRefresh} disabled={loading}>{loading ? "Loading..." : "Refresh"}</button>
      </header>
      <div className="segmented" role="group" aria-label="Artifact scope">
        <button type="button" className={scope === "task" ? "active" : ""} aria-pressed={scope === "task"} disabled={!hasTask} onClick={() => setScope("task")}>
          This task <span>{taskArtifactIds.length}</span>
        </button>
        <button type="button" className={scope === "all" ? "active" : ""} aria-pressed={scope === "all"} onClick={() => setScope("all")}>
          All <span>{artifacts.length}</span>
        </button>
      </div>
      {error && <div className="error-inline" role="alert">{error}</div>}
      {visible.length === 0 ? (
        <p className="empty">
          {loading ? "Loading artifacts..." : scope === "task" ? "This task has not produced any artifacts yet." : "No artifacts saved yet."}
        </p>
      ) : (
        <ul className="artifact-list">
          {visible.map((item) => (
            <li key={item.id}>
              <button type="button" className={`artifact-row ${taskIds.has(item.id) ? "current" : ""}`} onClick={() => setSelected(item.id)}>
                <span className="artifact-title">{item.title}</span>
                <span className="artifact-sub">
                  <span className="tag tag-tool">{humanize(item.artifact_type)}</span>
                  <span className="tag">{item.agent}</span>
                  <span className="tag">{item.status}</span>
                  <time className="trace-time" dateTime={item.updated_at}>{formatDate(item.updated_at)}</time>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {selected && <ArtifactDetail id={selected} onClose={() => setSelected(null)} />}
    </section>
  );
}
