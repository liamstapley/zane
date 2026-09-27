import json
from datetime import datetime, timezone
from uuid import uuid4

from app.db.database import Database
from app.schemas.artifacts import Artifact, ArtifactSummary, ArtifactType


class ArtifactNotFound(Exception):
    pass


class ArtifactService:
    def __init__(self, database: Database):
        self.database = database

    def create(self, task_id: str, agent: str, kind: ArtifactType, title: str, content: str) -> Artifact:
        now = datetime.now(timezone.utc).isoformat()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO artifacts(id,task_id,agent,artifact_type,title,content,created_at,updated_at,status,metadata) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (uuid4().hex, task_id, agent, kind.value, title, content, now, now, "ready", "{}"),
            )
        return self.by_task(task_id)

    def by_task(self, task_id: str) -> Artifact:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM artifacts WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise ArtifactNotFound(task_id)
        return self._parse(row)

    def get(self, artifact_id: str) -> Artifact:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM artifacts WHERE id=?", (artifact_id,)).fetchone()
        if row is None:
            raise ArtifactNotFound(artifact_id)
        return self._parse(row)

    def list(self) -> list[ArtifactSummary]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM artifacts ORDER BY created_at DESC").fetchall()
        return [ArtifactSummary.model_validate(self._parse(row).model_dump(exclude={"content"})) for row in rows]

    @staticmethod
    def _parse(row) -> Artifact:
        return Artifact.model_validate({**dict(row), "metadata": json.loads(row["metadata"])})
