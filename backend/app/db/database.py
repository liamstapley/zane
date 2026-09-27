import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any


FIXTURES = Path(__file__).parent / "fixtures"


class Database:
    def __init__(self, path: Path):
        self.path = path
        self._transaction: ContextVar[sqlite3.Connection | None] = ContextVar("zane_transaction", default=None)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        active = self._transaction.get()
        if active is not None:
            yield active
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        if self._transaction.get() is not None:
            raise RuntimeError("Nested write transaction is not supported")
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            token = self._transaction.set(connection)
            try:
                yield connection
            finally:
                self._transaction.reset(token)

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL,
                    agent TEXT,
                    skill TEXT,
                    result TEXT,
                    proposal_tool TEXT,
                    proposal_args TEXT,
                    proposal_summary TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    task_id TEXT NOT NULL REFERENCES tasks(id),
                    agent TEXT,
                    event_type TEXT NOT NULL,
                    tool TEXT,
                    skill TEXT,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS records (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY(namespace, key)
                );
                CREATE TABLE IF NOT EXISTS memory (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY(namespace, key)
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL UNIQUE REFERENCES tasks(id),
                    agent TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS clarification_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL REFERENCES tasks(id),
                    question TEXT NOT NULL,
                    answer TEXT
                );
                """
            )
            self._seed(connection)

    def _seed(self, connection: sqlite3.Connection) -> None:
        for namespace, groups in (("henhacks", ("threads", "tracker")), ("cssg", ("minutes", "updates", "actions"))):
            fixture = json.loads((FIXTURES / f"{namespace}.json").read_text(encoding="utf-8"))
            for group in groups:
                for item in fixture[group]:
                    connection.execute(
                        "INSERT OR IGNORE INTO records(namespace, key, value) VALUES (?, ?, ?)",
                        (namespace, f"{group}:{item['id']}", json.dumps(item)),
                    )

    def reset_demo(self) -> None:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute(
                "SELECT 1 FROM tasks WHERE status IN ('PROPOSED', 'APPROVED', 'EXECUTING') LIMIT 1"
            ).fetchone():
                raise ValueError("Cannot reset while a task is executing")
            for table in ("artifacts", "clarification_turns", "events", "tasks", "memory", "records"):
                connection.execute(f"DELETE FROM {table}")
            self._seed(connection)

    def get_record(self, namespace: str, key: str) -> dict[str, Any]:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT value FROM records WHERE namespace = ? AND key = ?", (namespace, key)
            ).fetchone()
        if row is None:
            raise KeyError(f"No {namespace} record: {key}")
        return json.loads(row["value"])

    def list_records(self, namespace: str, group: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT value FROM records WHERE namespace = ? AND key LIKE ? ORDER BY key",
                (namespace, f"{group}:%"),
            ).fetchall()
        return [json.loads(row["value"]) for row in rows]

    def put_record(self, namespace: str, key: str, value: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO records(namespace, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(namespace, key) DO UPDATE SET value = excluded.value",
                (namespace, key, json.dumps(value)),
            )
