from collections.abc import Callable

from app.memory.store import ScopedMemory
from app.models.provider import ModelProvider
from app.schemas.agent import AgentManifest
from app.services.runtime import AgentResult, EventSink, MutationProposal, load_skill
from app.services.prose import polish
from app.tools.registry import BoundTools


class HenHacksRuntime:
    def __init__(self, manifest: AgentManifest, provider: ModelProvider | None = None):
        self.manifest = manifest
        self.provider = provider

    def run(
        self,
        message: str,
        tools_for_skill: Callable[[str], BoundTools],
        memory: ScopedMemory,
        emit: EventSink,
    ) -> AgentResult:
        text = message.lower()
        if "perk" in text:
            skill = "sponsor_perk_tracking"
        elif "follow" in text:
            skill = "sponsor_followup"
        elif "draft" in text or "respond" in text or "reply" in text:
            skill = "sponsor_response_drafting"
        elif "triage" in text or "label" in text:
            skill = "sponsor_email_triage"
        elif "status" in text or "summar" in text or "tracker" in text:
            skill = "sponsorship_status_summary"
        else:
            return AgentResult("Which HenHacks task: triage, follow-up, draft, status summary, or perk tracking?", clarification=True)

        instructions = load_skill(self.manifest, skill)
        emit("henhacks", "skill_loaded", None, skill, "active", f"Loaded {skill} only.")
        tools = tools_for_skill(skill)
        if skill == "sponsorship_status_summary":
            tracker = tools.read("read_sponsor_tracker").data
            threads = tools.read("search_sponsor_emails", {"query": ""}).data
            summary = "; ".join(f"{item['sponsor']}: {item['status']} ({item['perk']})" for item in tracker)
            draft = f"Sponsor tracker: {summary}. Reviewed {len(threads)} email threads."
            return AgentResult(polish(self.provider, "henhacks", skill, instructions, summary, draft, emit), skill)

        if skill == "sponsor_perk_tracking":
            tracker = tools.read("read_sponsor_tracker").data
            sponsor = next((item for item in tracker if item["sponsor"].lower() in text), None)
            if sponsor is None:
                return AgentResult("Which sponsor's perk should be updated?", skill, clarification=True)
            perk = message.partition(" to ")[2].strip()
            if not perk:
                return AgentResult("What perk value should be recorded? Use 'to <new perk>'.", skill, clarification=True)
            args = tools.propose("update_sponsor_tracker", {"id": sponsor["id"], "perk": perk})
            return AgentResult(
                f"Proposed perk update for {sponsor['sponsor']}: {perk}.",
                skill,
                MutationProposal("update_sponsor_tracker", args, f"Update {sponsor['sponsor']}'s perk to {perk}."),
            )

        threads = tools.read("search_sponsor_emails", {"query": ""}).data
        thread = next((item for item in threads if item["sponsor"].lower() in text), None)
        if thread is None:
            return AgentResult("Which sponsor thread should I use? Specify Northstar Labs or Riverbend Software.", skill, clarification=True)
        thread = tools.read("read_email_thread", {"id": thread["id"]}).data
        if skill == "sponsor_email_triage":
            label = "Confirmed" if "confirmed" in thread["message"].lower() else "Needs follow-up"
            args = tools.propose("apply_henhacks_label", {"id": thread["id"], "label": label})
            return AgentResult(
                f"Thread {thread['subject']} appears to need the label {label}.",
                skill,
                MutationProposal("apply_henhacks_label", args, f"Apply {label} to {thread['sponsor']} thread."),
            )

        if skill == "sponsor_followup":
            tracker = tools.read("read_sponsor_tracker").data
            entry = next(item for item in tracker if item["id"] == thread["id"])
            content = (
                f"Hello {thread['sponsor']} team,\n\nFollowing up about HenHacks sponsorship. "
                f"Our tracker has the {entry['tier']} tier marked {entry['status'].lower()} "
                f"and the perk as {entry['perk']}. Could you share your next steps?\n\nThank you,\nHenHacks"
            )
        else:
            content = (
                f"Hello {thread['sponsor']} team,\n\nThank you for your note about "
                f"{thread['subject']}. We will review your question and follow up with "
                "the relevant details.\n\nBest,\nHenHacks"
            )
        content = polish(self.provider, "henhacks", skill, instructions, thread["message"], content, emit)
        args = tools.propose("create_email_draft_document", {"content": content})
        return AgentResult(
            f"Prepared an unsent sponsor draft for {thread['sponsor']}.",
            skill,
            MutationProposal("create_email_draft_document", args, f"Create an unsent {thread['sponsor']} email draft."),
        )
