from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.events import ExecutionEvent


class TaskStatus(StrEnum):
    PROPOSED = "PROPOSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class TaskRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class DecisionRequest(BaseModel):
    approved: bool


class Proposal(BaseModel):
    tool: str
    summary: str


class TaskSnapshot(BaseModel):
    id: str
    message: str
    status: TaskStatus
    agent: str | None
    skill: str | None
    result: str | None
    proposal: Proposal | None
    events: list[ExecutionEvent]
