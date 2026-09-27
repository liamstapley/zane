from collections.abc import Callable

from app.memory.store import ScopedMemory
from app.schemas.agent import AgentManifest
from app.services.runtime import AgentResult, EventSink, MutationProposal, load_skill
from app.tools.registry import BoundTools


class CSSGRuntime:
    def __init__(self, manifest: AgentManifest):
        self.manifest = manifest

    def run(
        self,
        message: str,
        tools_for_skill: Callable[[str], BoundTools],
        memory: ScopedMemory,
        emit: EventSink,
    ) -> AgentResult:
        text = message.lower()
        if "discord" in text or "check-in" in text or "checkin" in text:
            skill = "discord_checkin_draft"
        elif "agenda" in text:
            skill = "meeting_agenda"
        elif "minutes" in text:
            skill = "meeting_minutes"
        elif "action item" in text or "todo" in text:
            skill = "action_item_tracking"
        elif "project" in text or "status" in text or "summar" in text:
            skill = "project_status_summary"
        else:
            return AgentResult("Which CS+Social Good task: minutes, agenda, actions, project status, or Discord draft?", clarification=True)

        load_skill(self.manifest, skill)
        emit("cssg", "skill_loaded", None, skill, "active", f"Loaded {skill} only.")
        tools = tools_for_skill(skill)
        previous = tools.read("read_previous_meeting_minutes").data if skill in {"meeting_minutes", "meeting_agenda"} else []
        updates = tools.read("read_project_updates").data
        actions = tools.read("read_action_items").data
        projects = "; ".join(f"{item['project']}: {item['status']} ({item['detail']})" for item in updates)
        next_actions = "; ".join(f"{item['owner']}: {item['task']} (due {item['due']})" for item in actions)
        if skill == "project_status_summary":
            return AgentResult(f"Projects: {projects}. Next actions: {next_actions}.", skill)
        if skill == "action_item_tracking":
            return AgentResult(f"Action items: {next_actions}. Project context: {projects}.", skill)
        if skill == "meeting_agenda":
            return AgentResult(
                f"Proposed agenda: Review prior meeting ({previous[-1]['notes']}); "
                f"project updates ({projects}); action items ({next_actions}).",
                skill,
            )
        if skill == "meeting_minutes":
            content = f"Meeting minutes draft\nPrior context: {previous[-1]['notes']}\nProject updates: {projects}\nAction items: {next_actions}"
            tool = "write_meeting_minutes"
            summary = "Save new CS+Social Good meeting minutes."
        else:
            content = f"Team check-in draft: Project updates: {projects}. Action items: {next_actions}."
            tool = "create_discord_message_draft"
            summary = "Create an unposted Discord check-in draft."
        args = tools.propose(tool, {"content": content})
        return AgentResult(f"Prepared {skill.replace('_', ' ')} for review.", skill, MutationProposal(tool, args, summary))
