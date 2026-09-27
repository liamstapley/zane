import json
import logging
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from app.db.database import Database
from app.memory.store import ScopedMemory
from app.routing.graph import build_graph
from app.routing.router import Router
from app.schemas.agent import AgentManifest
from app.schemas.events import ExecutionEvent
from app.schemas.tasks import Proposal, TaskSnapshot, TaskStatus
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

        def emit(agent: str | None, event_type: str, tool: str | None,
                 skill: str | None, status: str, summary: str) -> None:
            self._emit(task_id, agent, event_type, tool, skill, status, summary)

        try:
            state = self._graph.invoke({"message": message, "emit": emit})
        except (PermissionError, ValueError, KeyError, sqlite3.Error) as error:
            logger.exception("Task %s failed during execution", task_id)
            result = f"Task failed: {type(error).__name__}."
            self._set_task(task_id, TaskStatus.FAILED, agent=None, skill=None, result=result)
            emit(None, "task_failed", None, None, TaskStatus.FAILED.value, result)
            return self.get(task_id)
        outcome = state["outcome"]
        agent = state["agent"]
        if outcome.clarification:
            self._set_task(task_id, TaskStatus.FAILED, agent=agent, skill=outcome.skill, result=outcome.result)
            emit(agent, "clarification", None, outcome.skill, TaskStatus.FAILED.value, outcome.result)
        elif outcome.proposal is not None:
            proposal = outcome.proposal
            self._set_task(
                task_id, TaskStatus.AWAITING_APPROVAL, agent=agent, skill=outcome.skill,
                result=outcome.result, tool=proposal.tool, args=proposal.args, summary=proposal.summary,
            )
            emit(agent, "approval_requested", proposal.tool, outcome.skill, TaskStatus.AWAITING_APPROVAL.value, proposal.summary)
        else:
            self._set_task(task_id, TaskStatus.EXECUTING, agent=agent, skill=outcome.skill, result=None)
            emit(agent, "task_status", None, outcome.skill, TaskStatus.EXECUTING.value, "Preparing final result.")
            self._set_task(task_id, TaskStatus.COMPLETED, agent=agent, skill=outcome.skill, result=outcome.result)
            emit(agent, "task_completed", None, outcome.skill, TaskStatus.COMPLETED.value, "Task completed.")
        return self.get(task_id)

    def get(self, task_id: str) -> TaskSnapshot:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            if row is None:
                raise TaskNotFound(task_id)
            event_rows = connection.execute(
                "SELECT timestamp, task_id, agent, event_type, tool, skill, status, summary "
                "FROM events WHERE task_id = ? ORDER BY id", (task_id,),
            ).fetchall()
        status = TaskStatus(row["status"])
        return TaskSnapshot(
            id=row["id"], message=row["message"], status=status, agent=row["agent"], skill=row["skill"],
            result=row["result"],
            proposal=Proposal(tool=row["proposal_tool"], summary=row["proposal_summary"])
            if status == TaskStatus.AWAITING_APPROVAL else None,
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
            output = self.registry.execute(agent, skill, tool, args, mutating=True)
        except (PermissionError, ValueError, KeyError, sqlite3.Error) as error:
            logger.exception("Approved task %s failed", task_id)
            self._set_task(task_id, TaskStatus.FAILED, agent=agent, skill=skill, result=f"Approved operation failed: {type(error).__name__}.")
            self._emit(task_id, agent, "task_failed", tool, skill, TaskStatus.FAILED.value, f"Approved operation failed: {type(error).__name__}.")
            return self.get(task_id)
        self._emit(task_id, agent, "tool_result", tool, skill, TaskStatus.COMPLETED.value, output.summary)
        self._set_task(
            task_id, TaskStatus.COMPLETED, agent=agent, skill=skill,
            result=f"{row['result']} {output.summary}",
        )
        self._emit(task_id, agent, "task_completed", None, skill, TaskStatus.COMPLETED.value, "Task completed.")
        return self.get(task_id)
