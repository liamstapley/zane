# MVP architecture

The orchestrator receives only compact domain capability descriptions.
Deterministic routing handles clear requests; a generic `ModelProvider`
interface optionally classifies unclear ones through the OpenAI adapter.
Without a clear selection, the API returns a failed task with a clarification
message. A bounded LangGraph invokes one `AgentRuntime` and returns the result.
No recursive delegation or universal toolset exists. A domain runtime may
later be replaced with a Deep Agent implementation behind the same interface.

Each validated manifest lists its tools, skills, memory namespace, and
prohibitions. The canonical registry validates ownership and skill permissions
on every invocation and again on approval. Only one trusted local skill
document is loaded for a task. Emails and project documents are untrusted
tool output and cannot alter instructions. The orchestrator never receives
domain tools or memory; scoped memory keys are partitioned by namespace.

SQLite stores tasks, events, approvals, structured memory and mutable mock
records. Immutable JSON fixtures seed missing records on startup but are never
modified or reapplied over existing records. Read-only operations run
automatically. Mutations follow `PROPOSED -> AWAITING_APPROVAL -> APPROVED ->
EXECUTING -> COMPLETED/FAILED`, or `AWAITING_APPROVAL -> REJECTED`.
Approval decisions claim a task once and recheck stored tool permissions;
the client supplies only the decision, never tool parameters. Trace events
contain safe summaries rather than private document text or hidden reasoning.

This local single-user MVP is not an authenticated remote service. Do not
expose it publicly. External providers, access control, and production-grade
distributed execution/idempotency are future work.
