from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class AgentManifest(BaseModel):
    name: str
    description: str
    responsibilities: list[str] = Field(min_length=1)
    allowed_tools: list[str]
    allowed_skills: list[str]
    memory_namespace: str
    prohibited_capabilities: list[str]

    @model_validator(mode="after")
    def validate_unique_permissions(self) -> "AgentManifest":
        if len(self.allowed_tools) != len(set(self.allowed_tools)):
            raise ValueError("Duplicate tool permissions")
        if len(self.allowed_skills) != len(set(self.allowed_skills)):
            raise ValueError("Duplicate skill permissions")
        if self.memory_namespace not in {"global", "henhacks", "cssg"}:
            raise ValueError("Invalid memory namespace")
        return self


def load_manifest(path: Path) -> AgentManifest:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return AgentManifest.model_validate(data)
