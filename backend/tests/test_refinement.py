import httpx
import pytest
from fastapi.testclient import TestClient

from app.agents.orchestrator.agent import load_domain_manifests
from app.config import Settings
from app.db.database import FIXTURES
from app.main import create_app
from app.memory.store import ScopedMemory
from app.routing.router import Router
from app.schemas.tasks import TaskStatus
from app.services.tasks import InvalidDecision


def test_clarification_resumes_original_task_across_restart(tmp_path):
    settings = Settings(zane_database_path=tmp_path / "demo.db")
    with TestClient(create_app(settings)) as client:
        first = client.post("/api/tasks", json={"message": "Draft follow-ups for HenHacks sponsors who haven't responded"}).json()
        assert first["status"] == "AWAITING_CLARIFICATION"
        assert first["agent"] == "henhacks"
        assert first["skill"] == "sponsor_followup"
    with TestClient(create_app(settings)) as client:
        assert client.get(f"/api/tasks/{first['id']}").json()["clarification_history"][0]["answer"] is None
        resumed = client.post(f"/api/tasks/{first['id']}/clarify", json={"answer": "Northstar Labs"}).json()
        assert resumed["id"] == first["id"]
        assert resumed["status"] == "AWAITING_APPROVAL"
        assert resumed["clarification_history"][0]["answer"] == "Northstar Labs"
        assert client.post(f"/api/tasks/{first['id']}/clarify", json={"answer": "Riverbend"}).status_code == 409
        assert client.get("/api/artifacts").json() == []
        approved = client.post(f"/api/tasks/{first['id']}/decision", json={"approved": True}).json()
        assert approved["status"] == "COMPLETED"
        assert len(approved["artifact_ids"]) == 1
        artifact = client.get(f"/api/artifacts/{approved['artifact_ids'][0]}").json()
        assert artifact["task_id"] == first["id"]
        assert artifact["artifact_type"] == "email_draft"
        assert "Northstar Labs" in artifact["content"]
        exported = client.get(f"/api/artifacts/{artifact['id']}/export")
        assert exported.status_code == 200
        assert exported.headers["content-disposition"].endswith('.md"')
        assert exported.content.startswith(b"# ")


def test_readonly_artifact_and_confirmed_full_reset(tmp_path):
    settings = Settings(zane_database_path=tmp_path / "demo.db")
    fixture_before = (FIXTURES / "henhacks.json").read_bytes()
    with TestClient(create_app(settings)) as client:
        ScopedMemory(client.app.state.tasks.database, "henhacks").put("demo-note", {"value": "temporary"})
        task = client.post("/api/tasks", json={"message": "Prepare CS+Social Good meeting agenda"}).json()
        assert task["status"] == "COMPLETED"
        assert len(task["artifact_ids"]) == 1
        assert client.get("/api/artifacts").json()[0]["artifact_type"] == "meeting_agenda"
        changed = client.post("/api/tasks", json={"message": "Update HenHacks sponsor perk for Northstar Labs to Demo perk"}).json()
        client.post(f"/api/tasks/{changed['id']}/decision", json={"approved": True})
        assert client.post("/api/demo/reset", json={"confirmation": "no"}).status_code == 400
        assert client.post("/api/demo/reset", json={"confirmation": "RESET DEMO DATA"}).json()["status"] == "reset"
        assert client.get("/api/artifacts").json() == []
        assert client.get(f"/api/tasks/{task['id']}").status_code == 404
        caps = client.get("/api/capabilities").json()
        assert {cap["name"] for cap in caps} == {"orchestrator", "henhacks", "cssg"}
        assert not next(cap for cap in caps if cap["name"] == "orchestrator")["allowed_tools"]
        assert ScopedMemory(client.app.state.tasks.database, "henhacks").get("demo-note") is None
        status = client.post("/api/tasks", json={"message": "Summarize HenHacks sponsorship status"}).json()
        assert "Workshop discussion pending" in status["result"]
    assert (FIXTURES / "henhacks.json").read_bytes() == fixture_before


def test_rejected_write_never_creates_artifact_and_approved_minutes_persist(tmp_path):
    settings = Settings(zane_database_path=tmp_path / "demo.db")
    with TestClient(create_app(settings)) as client:
        rejected = client.post("/api/tasks", json={"message": "Write CS+Social Good meeting minutes"}).json()
        assert rejected["artifact_ids"] == []
        assert client.post(f"/api/tasks/{rejected['id']}/decision", json={"approved": False}).json()["artifact_ids"] == []
        approved = client.post("/api/tasks", json={"message": "Write CS+Social Good meeting minutes"}).json()
        completed = client.post(f"/api/tasks/{approved['id']}/decision", json={"approved": True}).json()
        assert len(completed["artifact_ids"]) == 1
        assert client.get("/api/artifacts").json()[0]["artifact_type"] == "meeting_minutes"
    with TestClient(create_app(settings)) as client:
        artifact = client.get(f"/api/artifacts/{completed['artifact_ids'][0]}").json()
        assert artifact["task_id"] == approved["id"]
        assert client.post(f"/api/tasks/{approved['id']}/decision", json={"approved": True}).status_code == 409
        assert len(client.get("/api/artifacts").json()) == 1


def test_optional_ollama_provider_does_not_contact_server_until_invoked(tmp_path):
    app = create_app(Settings(zane_database_path=tmp_path / "demo.db", zane_model_provider="ollama",
                              zane_ollama_base_url="http://127.0.0.1:1"))
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        # Obvious deterministic route has no model dependency; generation failure falls back.
        task = client.post("/api/tasks", json={"message": "Summarize HenHacks sponsorship status"}).json()
        assert task["status"] == "COMPLETED"
        assert any(event["event_type"] == "model_fallback" for event in task["events"])
        ambiguous = client.post("/api/tasks", json={"message": "Please help"}).json()
        assert ambiguous["status"] == "AWAITING_CLARIFICATION"
        assert any(event["event_type"] == "model_fallback" for event in ambiguous["events"])


def test_ollama_endpoint_is_local_only(tmp_path):
    with pytest.raises(ValueError, match="local HTTP"):
        create_app(Settings(zane_database_path=tmp_path / "demo.db", zane_model_provider="ollama",
                            zane_ollama_base_url="https://external.example"))


def test_model_context_isolation_and_fallback(tmp_path):
    from app.db.database import Database
    from app.services.prose import polish

    class Provider:
        def classify_domain(self, message, capabilities):
            assert set(capabilities) == {"henhacks", "cssg"}
            return None

        def generate(self, agent, skill, instructions, context, draft):
            assert agent == "henhacks"
            assert skill == "sponsor_followup"
            assert "follow-up" in instructions.lower()
            assert "Silver tier" in context
            assert "Northstar Labs" in draft
            assert "Volunteer onboarding" not in context
            assert "meeting_minutes" not in instructions
            return draft

    from app.agents.henhacks.agent import HenHacksRuntime
    from app.agents.cssg.agent import CSSGRuntime
    from app.services.tasks import TaskService
    db = Database(tmp_path / "ctx.db")
    db.initialize()
    manifests = load_domain_manifests()
    provider = Provider()
    service = TaskService(
        db, Router(manifests, provider),
        {"henhacks": HenHacksRuntime(manifests["henhacks"], provider), "cssg": CSSGRuntime(manifests["cssg"], provider)},
        manifests,
    )
    assert service.create("Follow up HenHacks sponsor Northstar Labs").status == TaskStatus.AWAITING_APPROVAL

    class Unavailable:
        def generate(self, agent, skill, instructions, context, draft):
            raise httpx.ConnectError("offline")

    events = []
    assert polish(Unavailable(), "cssg", "meeting_minutes", "trusted", "untrusted", "draft", lambda *event: events.append(event)) == "draft"
    assert events[0][1] == "model_fallback"


def test_repeated_clarification_and_orchestrator_resume(service):
    task = service.create("Please help")
    assert task.status == TaskStatus.AWAITING_CLARIFICATION
    still_unclear = service.clarify(task.id, "something")
    assert still_unclear.status == TaskStatus.AWAITING_CLARIFICATION
    assert len(still_unclear.clarification_history) == 2
    resolved = service.clarify(task.id, "HenHacks sponsorship status summary")
    assert resolved.status == TaskStatus.COMPLETED
    assert resolved.agent == "henhacks"
    assert len(resolved.clarification_history) == 2
    with pytest.raises(InvalidDecision):
        service.clarify(task.id, "more")
