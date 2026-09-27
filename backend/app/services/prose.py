import logging

import httpx
import ollama

from app.models.provider import ModelProvider
from app.services.runtime import EventSink

logger = logging.getLogger(__name__)


def polish(
    provider: ModelProvider | None, agent: str, skill: str, instructions: str,
    context: str, draft: str, emit: EventSink,
) -> str:
    if provider is None:
        return draft
    try:
        text = provider.generate(agent, skill, instructions, context, draft)
    except (httpx.HTTPError, ollama.ResponseError, TimeoutError, ConnectionError, OSError) as error:
        logger.warning("Model unavailable for %s/%s: %s", agent, skill, type(error).__name__)
        emit(agent, "model_fallback", None, skill, "fallback", "Model unavailable; used local deterministic text.")
        return draft
    if not text or text.casefold() in {"none", "null", "n/a"} or len(text) > 4000:
        emit(agent, "model_fallback", None, skill, "fallback", "Model output unusable; used local deterministic text.")
        return draft
    return text
