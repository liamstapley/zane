from typing import Protocol


class ModelProvider(Protocol):
    def classify_domain(self, message: str, capabilities: dict[str, str]) -> str | None:
        """Return a domain name or None when the choice is not certain."""

    def generate(self, agent: str, skill: str, instructions: str, context: str, draft: str) -> str:
        """Return task-scoped prose; never decide tools, permissions, or business rules."""
