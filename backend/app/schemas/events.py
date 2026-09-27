from datetime import datetime

from pydantic import BaseModel


class ExecutionEvent(BaseModel):
    timestamp: datetime
    task_id: str
    agent: str | None
    event_type: str
    tool: str | None = None
    skill: str | None = None
    status: str
    summary: str
