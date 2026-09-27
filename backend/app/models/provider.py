from typing import Protocol


class ModelProvider(Protocol):
    def classify_domain(self, message: str, capabilities: dict[str, str]) -> str | None:
        """Return a domain name or None when the choice is not certain."""
