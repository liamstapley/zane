from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.memory.store import ScopedMemory
from app.schemas.agent import AgentManifest
from app.tools.registry import BoundTools


EventSink = Callable[[str | None, str, str | None, str | None, str, str], None]


@dataclass(frozen=True)
class MutationProposal:
    tool: str
    args: dict[str, Any]
    summary: str


@dataclass(frozen=True)
class AgentResult:
    result: str
    skill: str | None = None
    proposal: MutationProposal | None = None
    clarification: bool = False


class AgentRuntime(Protocol):
    manifest: AgentManifest

    def run(
        self,
        message: str,
        tools_for_skill: Callable[[str], BoundTools],
        memory: ScopedMemory,
        emit: EventSink,
    ) -> AgentResult:
        """Execute one selected domain workflow without exposing another domain."""


def load_skill(manifest: AgentManifest, skill: str) -> str:
    if skill not in manifest.allowed_skills:
        raise PermissionError(f"Skill {skill} not allowed for {manifest.name}")
    path = Path(__file__).parents[1] / "agents" / manifest.name / "skills" / f"{skill}.md"
    instructions = path.read_text(encoding="utf-8")
    if not instructions.strip():
        raise ValueError(f"Empty skill: {skill}")
    return instructions
