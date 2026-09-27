import re
import logging
from collections.abc import Callable

import httpx
import ollama

from app.models.provider import ModelProvider
from app.schemas.agent import AgentManifest

logger = logging.getLogger(__name__)


class Router:
    def __init__(self, manifests: dict[str, AgentManifest], provider: ModelProvider | None = None):
        self._capabilities = {name: manifest.description for name, manifest in manifests.items()}
        self._provider = provider

    def select(self, message: str, on_fallback: Callable[[], None] | None = None) -> str | None:
        text = message.lower()
        hen = bool(re.search(r"\b(henhacks|sponsor(?:ship|s)?|sponsor emails?)\b", text))
        cssg = bool(
            re.search(r"\b(cs\s*\+\s*(?:social\s*good|sg)|cssg|social\s+good|discord|meeting|agenda|action items?|project updates?)\b", text)
        )
        if hen != cssg:
            return "henhacks" if hen else "cssg"
        if self._provider is None:
            return None
        try:
            selected = self._provider.classify_domain(message, self._capabilities)
        except (httpx.HTTPError, ollama.ResponseError, TimeoutError, ConnectionError, OSError) as error:
            logger.warning("Model routing unavailable: %s", type(error).__name__)
            if on_fallback is not None:
                on_fallback()
            return None
        return selected if selected in self._capabilities else None
