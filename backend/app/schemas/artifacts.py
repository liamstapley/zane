from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ArtifactType(StrEnum):
    EMAIL_DRAFT = "email_draft"
    MEETING_MINUTES = "meeting_minutes"
    MEETING_AGENDA = "meeting_agenda"
    DISCORD_DRAFT = "discord_draft"
    SPONSORSHIP_SUMMARY = "sponsorship_summary"
    PROJECT_STATUS_SUMMARY = "project_status_summary"


class ArtifactSummary(BaseModel):
    id: str
    task_id: str
    agent: str
    artifact_type: ArtifactType
    title: str
    created_at: datetime
    updated_at: datetime
    status: str
    metadata: dict[str, str] = Field(default_factory=dict)


class Artifact(ArtifactSummary):
    content: str
