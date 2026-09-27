import json
import logging
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from app.db.database import Database
from app.memory.store import ScopedMemory
from app.routing.graph import build_graph
from app.routing.router import Router
from app.schemas.artifacts import ArtifactType
from app.schemas.agent import AgentManifest
from app.schemas.events import ExecutionEvent
from app.schemas.tasks import ClarificationTurn, Proposal, TaskSnapshot, TaskStatus
from app.services.artifacts import ArtifactService
from app.services.runtime import AgentRuntime, EventSink
from app.tools.registry import ToolRegistry


logger = logging.getLogger(__name__)


class TaskNotFound(Exception):
    pass


class InvalidDecision(Exception):
    pass


class TaskService:
    def __init__(
        self,
        database: Database,
        router: Router,
        runtimes: dict[str, AgentRuntime],
        manifests: dict[str, AgentManifest],
    ):
        self.database = database
        self.artifacts = ArtifactService(database)
        self.registry = ToolRegistry(database, manifests)
        self._graph = build_graph(
            router,
            runtimes,
            lambda agent, skill, emit: self.registry.bind(
                agent,
                skill,
                lambda event_type, tool, summary: emit(
                    agent, event_type, tool, skill,
                    "executing" if event_type == "tool_call" else "completed", summary,
                ),
            ),
            lambda namespace: ScopedMemory(database, namespace),
        )

    def _emit(
        self, task_id: str, agent: str | None, event_type: str,
        tool: str | None, skill: str | None, status: str, summary: str,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO events(timestamp, task_id, agent, event_type, tool, skill, status, summary) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), task_id, agent, event_type, tool, skill, status, summary),
            )

    def _set_task(self, task_id: str, status: TaskStatus, *, agent: str | None, skill: str | None,
                  result: str | None, tool: str | None = None, args: dict | None = None,
                  summary: str | None = None) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE tasks SET status = ?, agent = ?, skill = ?, result = ?, "
                "proposal_tool = ?, proposal_args = ?, proposal_summary = ? WHERE id = ?",
                (status.value, agent, skill, result, tool, json.dumps(args) if args is not None else None, summary, task_id),
            )

    def create(self, message: str) -> TaskSnapshot:
        task_id = uuid4().hex
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO tasks(id, message, status) VALUES (?, ?, ?)",
                (task_id, message, TaskStatus.PROPOSED.value),
            )
        self._emit(task_id, None, "task_created", None, None, TaskStatus.PROPOSED.value, "Task proposed.")

        return self._run(task_id, message)

    def _run(self, task_id: str, message: str, routing_message: str | None = None,
             pinned_agent: str | None = None) -> TaskSnapshot:
        def emit(agent: str | None, event_type: str, tool: str | None,
                 skill: str | None, status: str, summary: str) -> None:
            self._emit(task_id, agent, event_type, tool, skill, status, summary)

        try:
            state = self._graph.invoke({
                "message": message, "routing_message": routing_message or message,
                "pinned_agent": pinned_agent, "emit": emit,
            })
        except (PermissionError, ValueError, KeyError, sqlite3.Error) as error:
            logger.exception("Task %s failed during execution", task_id)
            result = f"Task failed: {type(error).__name__}."
            self._set_task(task_id, TaskStatus.FAILED, agent=None, skill=None, result=result)
            emit(None, "task_failed", None, None, TaskStatus.FAILED.value, result)
            return self.get(task_id)
        outcome = state["outcome"]
        agent = state["agent"]
        if outcome.clarification:
            with self.database.connect() as connection:
                connection.execute(
                    "INSERT INTO clarification_turns(task_id,question) VALUES (?,?)",
                    (task_id, outcome.result),
                )
            self._set_task(task_id, TaskStatus.AWAITING_CLARIFICATION, agent=agent, skill=outcome.skill, result=outcome.result)
            emit(agent, "clarification", None, outcome.skill, TaskStatus.AWAITING_CLARIFICATION.value, "Additional information requested.")
        elif outcome.proposal is not None:
            proposal = outcome.proposal
            emit(agent, "mutation_proposed", proposal.tool, outcome.skill, TaskStatus.PROPOSED.value, proposal.summary)
            self._set_task(
                task_id, TaskStatus.AWAITING_APPROVAL, agent=agent, skill=outcome.skill,
                result=outcome.result, tool=proposal.tool, args=proposal.args, summary=proposal.summary,
            )
            emit(agent, "approval_requested", proposal.tool, outcome.skill, TaskStatus.AWAITING_APPROVAL.value, proposal.summary)
        else:
            read_artifacts = {
                "meeting_agenda": ArtifactType.MEETING_AGENDA,
                "sponsorship_status_summary": ArtifactType.SPONSORSHIP_SUMMARY,
                "project_status_summary": ArtifactType.PROJECT_STATUS_SUMMARY,
            }
            try:
                with self.database.transaction():
                    self._set_task(task_id, TaskStatus.EXECUTING, agent=agent, skill=outcome.skill, result=None)
                    emit(agent, "task_status", None, outcome.skill, TaskStatus.EXECUTING.value, "Preparing final result.")
                    if outcome.skill in read_artifacts and agent is not None:
                        artifact = self.artifacts.create(
                            task_id, agent, read_artifacts[outcome.skill],
                            outcome.skill.replace("_", " ").title(), outcome.result,
                        )
                        emit(agent, "artifact_created", None, outcome.skill, "completed", f"Saved local artifact {artifact.id}.")
                    self._set_task(task_id, TaskStatus.COMPLETED, agent=agent, skill=outcome.skill, result=outcome.result)
                    emit(agent, "task_completed", None, outcome.skill, TaskStatus.COMPLETED.value, "Task completed.")
            except sqlite3.Error as error:
                logger.exception("Task %s could not save its result", task_id)
                self._set_task(task_id, TaskStatus.FAILED, agent=agent, skill=outcome.skill,
                               result=f"Could not save task: {type(error).__name__}.")
                emit(agent, "task_failed", None, outcome.skill, TaskStatus.FAILED.value, "Could not save task result.")
        return self.get(task_id)

    def clarify(self, task_id: str, answer: str) -> TaskSnapshot:
        answer = answer.strip()
        if not answer or len(answer) > 2000:
            raise ValueError("Clarification answer must contain 1 to 2000 characters")
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                raise TaskNotFound(task_id)
            if row["status"] != TaskStatus.AWAITING_CLARIFICATION.value:
                raise InvalidDecision("Task is not awaiting clarification.")
            turns = connection.execute(
                "SELECT id,answer FROM clarification_turns WHERE task_id=? ORDER BY id", (task_id,)
            ).fetchall()
            if not turns or turns[-1]["answer"] is not None:
                raise InvalidDecision("No unanswered clarification for this task.")
            connection.execute("UPDATE clarification_turns SET answer=? WHERE id=?", (answer, turns[-1]["id"]))
            connection.execute("UPDATE tasks SET status=? WHERE id=?", (TaskStatus.PROPOSED.value, task_id))
            previous = connection.execute(
                "SELECT answer FROM clarification_turns WHERE task_id=? ORDER BY id", (task_id,)
            ).fetchall()
        self._emit(task_id, row["agent"], "clarification_received", None, row["skill"], "received", "Clarification received; resuming original task.")
        message = row["message"] + "\n" + "\n".join(turn["answer"] for turn in previous[-5:])
        return self._run(task_id, message, routing_message=answer, pinned_agent=row["agent"])

    def get(self, task_id: str) -> TaskSnapshot:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                raise TaskNotFound(task_id)
            event_rows = connection.execute(
                "SELECT timestamp, task_id, agent, event_type, tool, skill, status, summary "
                "FROM events WHERE task_id = ? ORDER BY id", (task_id,),
            ).fetchall()
            turns = connection.execute(
                "SELECT question,answer FROM clarification_turns WHERE task_id=? ORDER BY id", (task_id,)
            ).fetchall()
            artifacts = connection.execute("SELECT id FROM artifacts WHERE task_id=?", (task_id,)).fetchall()
        status = TaskStatus(row["status"])
        return TaskSnapshot(
            id=row["id"], message=row["message"], status=status, agent=row["agent"], skill=row["skill"],
            result=row["result"],
            proposal=Proposal(tool=row["proposal_tool"], summary=row["proposal_summary"])
            if status == TaskStatus.AWAITING_APPROVAL else None,
            clarification_history=[ClarificationTurn.model_validate(dict(turn)) for turn in turns],
            artifact_ids=[artifact["id"] for artifact in artifacts],
            events=[ExecutionEvent.model_validate(dict(event)) for event in event_rows],
        )

    def decide(self, task_id: str, approved: bool) -> TaskSnapshot:
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                raise TaskNotFound(task_id)
            if row["status"] != TaskStatus.AWAITING_APPROVAL.value:
                raise InvalidDecision(f"Task {task_id} is not awaiting approval.")
            status = TaskStatus.APPROVED if approved else TaskStatus.REJECTED
            connection.execute("UPDATE tasks SET status = ? WHERE id = ?", (status.value, task_id))
        agent, skill, tool = row["agent"], row["skill"], row["proposal_tool"]
        if not approved:
            self._emit(task_id, agent, "approval_rejected", tool, skill, TaskStatus.REJECTED.value, "Proposal rejected; no changes made.")
            return self.get(task_id)
        self._emit(task_id, agent, "approval_granted", tool, skill, TaskStatus.APPROVED.value, "Proposal approved.")
        try:
            args = json.loads(row["proposal_args"])
            self.registry.validate(agent, skill, tool, mutating=True)
            with self.database.connect() as connection:
                connection.execute(
                    "UPDATE tasks SET status = ? WHERE id = ? AND status = ?",
                    (TaskStatus.EXECUTING.value, task_id, TaskStatus.APPROVED.value),
                )
            self._emit(task_id, agent, "tool_call", tool, skill, TaskStatus.EXECUTING.value, "Executing approved operation.")
            with self.database.transaction():
                output = self.registry.execute(agent, skill, tool, args, mutating=True)
                artifact_types = {
                    "create_email_draft_document": ArtifactType.EMAIL_DRAFT,
                    "write_meeting_minutes": ArtifactType.MEETING_MINUTES,
                    "create_discord_message_draft": ArtifactType.DISCORD_DRAFT,
                }
                if tool in artifact_types:
                    artifact = self.artifacts.create(
                        task_id, agent, artifact_types[tool], skill.replace("_", " ").title(),
                        args["content"],
                    )
                    self._emit(task_id, agent, "artifact_created", tool, skill, "completed", f"Saved local artifact {artifact.id}.")
                self._emit(task_id, agent, "tool_result", tool, skill, TaskStatus.COMPLETED.value, output.summary)
                self._set_task(
                    task_id, TaskStatus.COMPLETED, agent=agent, skill=skill,
                    result=f"{row['result']} {output.summary}",
                )
                self._emit(task_id, agent, "task_completed", None, skill, TaskStatus.COMPLETED.value, "Task completed.")
        except (PermissionError, ValueError, KeyError, sqlite3.Error) as error:
            logger.exception("Approved task %s failed", task_id)
            self._set_task(task_id, TaskStatus.FAILED, agent=agent, skill=skill, result=f"Approved operation failed: {type(error).__name__}.")
            self._emit(task_id, agent, "task_failed", tool, skill, TaskStatus.FAILED.value, f"Approved operation failed: {type(error).__name__}.")
            return self.get(task_id)
        return self.get(task_id)
