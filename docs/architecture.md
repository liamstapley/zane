# ZANE architecture

The orchestrator sees only compact capability descriptions and routes exactly
one selected agent. LangGraph makes the route/delegate path explicit; each
domain implements the replaceable `AgentRuntime` interface. The validated
manifests supply exact skill/tool allowlists and memory namespaces. The
registry checks each call and approved mutation again. No agent has send
tools or access to another domain's memory/toolset.

Deterministic intent selection loads exactly one local skill document. Fixture
text, clarification answers, and model responses are untrusted data, not
instructions. An optional provider-neutral model boundary supports compact
domain classification and task-scoped prose. The thin Ollama adapter uses a
local Ollama instance started separately by the user; OpenAI is a separate
optional adapter. Neither model chooses tools, approvals, eligibility or
state transitions. Failed model calls fall back to deterministic generation.

SQLite persists task statuses, event summaries, clarification question/answer
turns, approved proposal parameters, mutable demo records, scoped structured
memory, and local task-linked artifacts. `POST /api/tasks/{id}/clarify` resumes
the original task ID and preserves its selected domain across short answers.
Approved document writes and artifact creation happen in one SQLite write
transaction. Unique task linkage prevents duplicate artifacts on replay.
Read-only agendas/summaries also become artifacts on completion. The artifact
API provides list, detail, and Markdown download. No private source body is
placed in the trace.

Demo reset requires both client confirmation and the explicit server token
`RESET DEMO DATA`. It clears tasks, events, artifacts, memory and mutable
records, then reseeds SQLite from immutable JSON. Active execution is not
reset. The app assumes one local user; remote deployment requires auth and
stronger data-protection measures.
