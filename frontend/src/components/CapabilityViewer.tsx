import { useEffect, useState } from "react";
import { getCapabilities } from "../api";
import type { AgentCapability } from "../types";
import Modal from "./Modal";

interface Props {
  onClose: () => void;
  activeAgent: string | null;
}

function List({ title, items, mono, empty }: { title: string; items: string[]; mono?: boolean; empty: string }) {
  return (
    <div className="cap-section">
      <span className="label">{title}</span>
      {items.length === 0 ? (
        <p className="empty">{empty}</p>
      ) : mono ? (
        <div className="tag-row">{items.map((item) => <span className="tag tag-tool mono" key={item}>{item}</span>)}</div>
      ) : (
        <ul className="cap-bullets">{items.map((item) => <li key={item}>{item}</li>)}</ul>
      )}
    </div>
  );
}

export default function CapabilityViewer({ onClose, activeAgent }: Props) {
  const [capabilities, setCapabilities] = useState<AgentCapability[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCapabilities()
      .then((value) => { if (!cancelled) setCapabilities(value); })
      .catch((cause: unknown) => { if (!cancelled) setError(cause instanceof Error ? cause.message : "Unable to load capabilities."); });
    return () => { cancelled = true; };
  }, []);

  return (
    <Modal title="Agent capabilities" onClose={onClose} wide>
      <p className="panel-sub">Each agent is isolated to its own tools, skills and memory namespace. Mutating tools always require your approval.</p>
      {error && <div className="error-inline" role="alert">{error}</div>}
      {!capabilities && !error && <p className="empty">Loading capabilities...</p>}
      {capabilities && capabilities.length === 0 && <p className="empty">No agents registered.</p>}
      {capabilities && capabilities.length > 0 && (
        <div className="cap-grid">
          {capabilities.map((cap) => (
            <article key={cap.name} className={`cap-card ${activeAgent === cap.name ? "active" : ""}`}>
              <header className="panel-header">
                <h3>{cap.name}</h3>
                <span className="badge">memory: {cap.memory_namespace}</span>
              </header>
              {activeAgent === cap.name && <span className="badge badge-busy cap-active">HANDLING CURRENT TASK</span>}
              <p className="task-message">{cap.description}</p>
              <List title="Responsibilities" items={cap.responsibilities} empty="None listed." />
              <List title="Allowed tools" items={cap.allowed_tools} mono empty="No tools - routing only." />
              <List title="Allowed skills" items={cap.allowed_skills} mono empty="No skills." />
              {cap.prohibited_capabilities && cap.prohibited_capabilities.length > 0 && (
                <List title="Prohibited" items={cap.prohibited_capabilities} empty="" />
              )}
            </article>
          ))}
        </div>
      )}
    </Modal>
  );
}
