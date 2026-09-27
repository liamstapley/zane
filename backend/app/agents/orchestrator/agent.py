from pathlib import Path

from app.routing.router import Router
from app.schemas.agent import AgentManifest, load_manifest


def load_domain_manifests() -> dict[str, AgentManifest]:
    root = Path(__file__).parents[1]
    orchestrator = load_manifest(root / "orchestrator" / "manifest.yaml")
    if orchestrator.allowed_tools or orchestrator.allowed_skills or orchestrator.memory_namespace != "global":
        raise ValueError("Orchestrator must have no domain capabilities")
    return {name: load_manifest(root / name / "manifest.yaml") for name in ("henhacks", "cssg")}


__all__ = ["Router", "load_domain_manifests"]
