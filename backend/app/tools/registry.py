from collections.abc import Callable
from typing import Any

from app.db.database import Database
from app.schemas.agent import AgentManifest
from app.tools.common.contracts import ToolOutput, ToolSpec
from app.tools.cssg.mock import TOOLS as CSSG_TOOLS
from app.tools.henhacks.mock import TOOLS as HENHACKS_TOOLS


SKILL_TOOLS: dict[str, dict[str, frozenset[str]]] = {
    "henhacks": {
        "sponsor_email_triage": frozenset({"search_sponsor_emails", "read_email_thread", "apply_henhacks_label"}),
        "sponsor_followup": frozenset({"search_sponsor_emails", "read_email_thread", "read_sponsor_tracker", "create_email_draft_document"}),
        "sponsor_response_drafting": frozenset({"search_sponsor_emails", "read_email_thread", "create_email_draft_document"}),
        "sponsorship_status_summary": frozenset({"read_sponsor_tracker", "search_sponsor_emails"}),
        "sponsor_perk_tracking": frozenset({"read_sponsor_tracker", "update_sponsor_tracker"}),
    },
    "cssg": {
        "meeting_minutes": frozenset({"read_previous_meeting_minutes", "read_project_updates", "read_action_items", "write_meeting_minutes"}),
        "meeting_agenda": frozenset({"read_previous_meeting_minutes", "read_project_updates", "read_action_items"}),
        "action_item_tracking": frozenset({"read_action_items", "read_project_updates"}),
        "project_status_summary": frozenset({"read_project_updates", "read_action_items"}),
        "discord_checkin_draft": frozenset({"read_project_updates", "read_action_items", "create_discord_message_draft"}),
    },
}


class ToolRegistry:
    def __init__(self, database: Database, manifests: dict[str, AgentManifest]):
        self._database = database
        self._specs: dict[str, ToolSpec] = {spec.name: spec for spec in (*HENHACKS_TOOLS, *CSSG_TOOLS)}
        if len(self._specs) != len(HENHACKS_TOOLS) + len(CSSG_TOOLS):
            raise ValueError("Duplicate canonical tool names")
        for agent, manifest in manifests.items():
            if agent not in SKILL_TOOLS or manifest.name != agent or manifest.memory_namespace != agent:
                raise ValueError(f"Invalid domain manifest: {agent}")
            if set(manifest.allowed_skills) != set(SKILL_TOOLS[agent]):
                raise ValueError(f"Skill inventory differs from manifest for {agent}")
            owned = {name for name, spec in self._specs.items() if spec.agent == agent}
            if set(manifest.allowed_tools) != owned:
                raise ValueError(f"Tool inventory differs from manifest for {agent}")
            if any(not allowed <= owned for allowed in SKILL_TOOLS[agent].values()):
                raise ValueError(f"Skill grants non-domain tool for {agent}")
        self._manifests = manifests

    def bind(self, agent: str, skill: str, on_tool: Callable[[str, str, str], None] | None = None) -> "BoundTools":
        if agent not in self._manifests or skill not in self._manifests[agent].allowed_skills:
            raise PermissionError("Agent or skill not permitted")
        return BoundTools(self, agent, skill, on_tool)

    def validate(self, agent: str, skill: str, tool: str, mutating: bool) -> ToolSpec:
        if agent not in self._manifests or skill not in self._manifests[agent].allowed_skills:
            raise PermissionError("Agent or skill not permitted")
        spec = self._specs.get(tool)
        if (
            spec is None
            or spec.agent != agent
            or tool not in self._manifests[agent].allowed_tools
            or tool not in SKILL_TOOLS[agent][skill]
            or spec.mutating != mutating
        ):
            raise PermissionError(f"Tool {tool} not permitted for {agent}/{skill}")
        return spec

    def execute(self, agent: str, skill: str, tool: str, args: dict[str, Any], *, mutating: bool) -> ToolOutput:
        spec = self.validate(agent, skill, tool, mutating)
        parsed = spec.input_type.model_validate(args)
        return spec.invoke(self._database, parsed)

    @property
    def tool_names(self) -> frozenset[str]:
        return frozenset(self._specs)


class BoundTools:
    def __init__(self, registry: ToolRegistry, agent: str, skill: str, on_tool: Callable[[str, str, str], None] | None):
        self._registry = registry
        self._agent = agent
        self._skill = skill
        self._on_tool = on_tool

    def read(self, name: str, args: dict[str, Any] | None = None) -> ToolOutput:
        self._registry.validate(self._agent, self._skill, name, mutating=False)
        if self._on_tool:
            self._on_tool("tool_call", name, "Invoking read-only tool.")
        output = self._registry.execute(self._agent, self._skill, name, args or {}, mutating=False)
        if self._on_tool:
            self._on_tool("tool_result", name, output.summary)
        return output

    def propose(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        spec = self._registry.validate(self._agent, self._skill, name, mutating=True)
        return spec.input_type.model_validate(args).model_dump()
