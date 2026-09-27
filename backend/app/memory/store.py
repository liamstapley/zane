import json
from typing import Any

from app.db.database import Database


class ScopedMemory:
    def __init__(self, database: Database, namespace: str):
        if namespace not in {"global", "henhacks", "cssg"}:
            raise ValueError("Invalid memory namespace")
        self._database = database
        self.namespace = namespace

    def get(self, key: str) -> dict[str, Any] | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT value FROM memory WHERE namespace = ? AND key = ?",
                (self.namespace, key),
            ).fetchone()
        return json.loads(row["value"]) if row else None

    def put(self, key: str, value: dict[str, Any]) -> None:
        with self._database.connect() as connection:
            connection.execute(
                "INSERT INTO memory(namespace, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(namespace, key) DO UPDATE SET value = excluded.value",
                (self.namespace, key, json.dumps(value)),
            )
