import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db.database import FIXTURES
from app.main import create_app
from app.memory.store import ScopedMemory
from app.routing.router import Router
from app.agents.orchestrator.agent import load_domain_manifests
from app.tools.registry import ToolRegistry
from app.schemas.tasks import TaskStatus
from app.services.tasks import InvalidDecision


def test_routes_and_readonly_result(service):
    hen = service.create("Summarize HenHacks sponsorship status")
    cssg = service.create("Summarize CS+Social Good project status")
    assert hen.agent == "henhacks"
    assert hen.skill == "sponsorship_status_summary"
    assert hen.status == TaskStatus.COMPLETED
    assert cssg.agent == "cssg"
    assert cssg.skill == "project_status_summary"
    assert cssg.status == TaskStatus.COMPLETED
    assert all(event.summary and event.task_id == hen.id for event in hen.events)


def test_domain_and_skill_isolation_and_no_send_tools(service):
    registry = service.registry
    assert not {"send_email", "send_discord_message"} & registry.tool_names
    for agent, skill, tool in [
        ("henhacks", "sponsor_email_triage", "read_project_updates"),
        ("cssg", "meeting_agenda", "read_sponsor_tracker"),
        ("henhacks", "sponsorship_status_summary", "apply_henhacks_label"),
    ]:
        with pytest.raises(PermissionError):
            registry.execute(agent, skill, tool, {}, mutating=False)
    with pytest.raises(PermissionError):
        registry.bind("orchestrator", "meeting_agenda")


def test_manifest_cannot_swap_memory_namespace(service):
    manifests = load_domain_manifests()
    manifests["henhacks"] = manifests["henhacks"].model_copy(update={"memory_namespace": "cssg"})
    with pytest.raises(ValueError, match="Invalid domain manifest"):
        ToolRegistry(service.database, manifests)


def test_mutation_requires_approval_and_persists_only_sqlite(service):
    fixture_before = (FIXTURES / "henhacks.json").read_bytes()
    task = service.create("Triage HenHacks sponsor email from Northstar Labs")
    assert task.status == TaskStatus.AWAITING_APPROVAL
    assert task.proposal.tool == "apply_henhacks_label"
    assert service.database.get_record("henhacks", "threads:northstar")["label"] == "Inbox"
    approved = service.decide(task.id, True)
    assert approved.status == TaskStatus.COMPLETED
    assert {"PROPOSED", "AWAITING_APPROVAL", "APPROVED", "EXECUTING", "COMPLETED"} <= {
        event.status for event in approved.events
    }
    assert service.database.get_record("henhacks", "threads:northstar")["label"] == "Needs follow-up"
    with pytest.raises(InvalidDecision):
        service.decide(task.id, True)
    perk = service.create("Update HenHacks sponsor perk for Northstar Labs to Mentorship lounge")
    assert perk.status == TaskStatus.AWAITING_APPROVAL
    assert service.database.get_record("henhacks", "tracker:northstar")["perk"] == "Workshop discussion pending"
    service.decide(perk.id, True)
    assert service.database.get_record("henhacks", "tracker:northstar")["perk"] == "Mentorship lounge"
    service.database.initialize()
    assert service.database.get_record("henhacks", "tracker:northstar")["perk"] == "Mentorship lounge"
    assert (FIXTURES / "henhacks.json").read_bytes() == fixture_before


def test_rejection_and_cssg_write(service):
    minutes = service.create("Write CS+Social Good meeting minutes")
    assert minutes.status == TaskStatus.AWAITING_APPROVAL
    assert len(service.database.list_records("cssg", "minutes")) == 1
    rejected = service.decide(minutes.id, False)
    assert rejected.status == TaskStatus.REJECTED
    assert len(service.database.list_records("cssg", "minutes")) == 1
    draft = service.create("Draft CS+Social Good Discord check-in")
    assert draft.status == TaskStatus.AWAITING_APPROVAL
    assert not service.database.list_records("cssg", "drafts")
    assert service.decide(draft.id, True).status == TaskStatus.COMPLETED
    assert len(service.database.list_records("cssg", "drafts")) == 1


def test_approval_revalidates_stored_tool_and_does_not_execute_cross_domain(service):
    task = service.create("Triage HenHacks sponsor email from Northstar Labs")
    with service.database.connect() as connection:
        connection.execute(
            "UPDATE tasks SET proposal_tool = ? WHERE id = ?",
            ("write_meeting_minutes", task.id),
        )
    failed = service.decide(task.id, True)
    assert failed.status == TaskStatus.FAILED
    assert len(service.database.list_records("cssg", "minutes")) == 1


@pytest.mark.parametrize(
    ("message", "skill", "status"),
    [
        ("Follow up HenHacks sponsor Northstar Labs", "sponsor_followup", TaskStatus.AWAITING_APPROVAL),
        ("Draft HenHacks sponsor response to Riverbend Software", "sponsor_response_drafting", TaskStatus.AWAITING_APPROVAL),
        ("Triage HenHacks sponsor email from Riverbend Software", "sponsor_email_triage", TaskStatus.AWAITING_APPROVAL),
        ("Summarize HenHacks sponsorship status", "sponsorship_status_summary", TaskStatus.COMPLETED),
        ("Update HenHacks sponsor perk for Northstar Labs to Mentorship lounge", "sponsor_perk_tracking", TaskStatus.AWAITING_APPROVAL),
        ("Write CS+Social Good meeting minutes", "meeting_minutes", TaskStatus.AWAITING_APPROVAL),
        ("Prepare CS+Social Good meeting agenda", "meeting_agenda", TaskStatus.COMPLETED),
        ("Review CS+Social Good action items", "action_item_tracking", TaskStatus.COMPLETED),
        ("Summarize CS+Social Good project status", "project_status_summary", TaskStatus.COMPLETED),
        ("Draft CS+Social Good Discord check-in", "discord_checkin_draft", TaskStatus.AWAITING_APPROVAL),
    ],
)
def test_each_skill_executes_with_trace(service, message, skill, status):
    task = service.create(message)
    assert (task.skill, task.status) == (skill, status)
    assert {event.event_type for event in task.events} >= {"routing", "skill_loaded", "tool_call", "tool_result"}
    assert {event.skill for event in task.events if event.skill} == {skill}


def test_clarification_and_memory_isolation(service):
    assert service.create("Hi").status == TaskStatus.AWAITING_CLARIFICATION
    assert service.create("Summarize HenHacks and CS+Social Good").status == TaskStatus.AWAITING_CLARIFICATION
    hen = ScopedMemory(service.database, "henhacks")
    cssg = ScopedMemory(service.database, "cssg")
    hen.put("note", {"value": "sponsor detail"})
    assert cssg.get("note") is None


def test_optional_provider_receives_only_compact_capabilities():
    class Provider:
        def classify_domain(self, message, capabilities):
            assert set(capabilities) == {"henhacks", "cssg"}
            assert all(isinstance(value, str) for value in capabilities.values())
            assert "allowed_tools" not in str(capabilities)
            return "henhacks"

    assert Router(load_domain_manifests(), Provider()).select("Please help") == "henhacks"


def test_api_end_to_end(tmp_path):
    app = create_app(Settings(zane_database_path=tmp_path / "api.db"))
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        response = client.post("/api/tasks", json={"message": "Draft HenHacks sponsor response to Riverbend Software"})
        assert response.status_code == 200
        task = response.json()
        assert task["status"] == "AWAITING_APPROVAL"
        assert task["agent"] == "henhacks"
        assert task["proposal"]["tool"] == "create_email_draft_document"
        assert client.get(f"/api/tasks/{task['id']}").json()["events"]
        decision = client.post(f"/api/tasks/{task['id']}/decision", json={"approved": True})
        assert decision.json()["status"] == "COMPLETED"
        assert client.post(f"/api/tasks/{task['id']}/decision", json={"approved": True}).status_code == 409
        assert client.get("/api/tasks/unknown").status_code == 404


def test_pending_approval_survives_app_restart(tmp_path):
    settings = Settings(zane_database_path=tmp_path / "restart.db")
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/tasks", json={"message": "Update HenHacks sponsor perk for Northstar Labs to Mentorship lounge"}
        )
        task_id = response.json()["id"]
        assert response.json()["status"] == "AWAITING_APPROVAL"
    with TestClient(create_app(settings)) as client:
        assert client.get(f"/api/tasks/{task_id}").json()["status"] == "AWAITING_APPROVAL"
        assert client.post(f"/api/tasks/{task_id}/decision", json={"approved": True}).json()["status"] == "COMPLETED"
