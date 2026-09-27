import re

from app.models.provider import ModelProvider
from app.schemas.agent import AgentManifest


class Router:
    def __init__(self, manifests: dict[str, AgentManifest], provider: ModelProvider | None = None):
        self._capabilities = {name: manifest.description for name, manifest in manifests.items()}
        self._provider = provider

    def select(self, message: str) -> str | None:
        text = message.lower()
        hen = bool(re.search(r"\b(henhacks|sponsor(?:ship|s)?|sponsor emails?)\b", text))
        cssg = bool(
            re.search(r"\b(cs\s*\+\s*(?:social\s*good|sg)|cssg|social\s+good|discord|meeting|agenda|action items?|project updates?)\b", text)
        )
        if hen != cssg:
            return "henhacks" if hen else "cssg"
        if self._provider is None:
            return None
        selected = self._provider.classify_domain(message, self._capabilities)
        return selected if selected in self._capabilities else None
