import pytest

from app.agents.cssg.agent import CSSGRuntime
from app.agents.henhacks.agent import HenHacksRuntime
from app.agents.orchestrator.agent import load_domain_manifests
from app.db.database import Database
from app.routing.router import Router
from app.services.tasks import TaskService


@pytest.fixture
def service(tmp_path):
    db = Database(tmp_path / "test.db")
    db.initialize()
    manifests = load_domain_manifests()
    return TaskService(
        db, Router(manifests),
        {"henhacks": HenHacksRuntime(manifests["henhacks"]), "cssg": CSSGRuntime(manifests["cssg"])},
        manifests,
    )
