"""Groq adapter using its OpenAI-compatible Chat Completions API."""

from __future__ import annotations

import httpx

from app.config import Settings
from app.core.errors import ConfigError
from app.providers.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    """Call Groq with a user-selected model and model-specific capabilities."""

    name = "groq"
    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        api_key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else ""
        if not api_key.strip():
            raise ConfigError("GROQ_API_KEY must be configured to use Groq.")
        if not settings.groq_model.strip():
            raise ConfigError("GROQ_MODEL must be configured to use Groq.")
        super().__init__(
            name=self.name,
            label="Groq",
            endpoint=self.endpoint,
            api_key=api_key,
            model=settings.groq_model.strip(),
            vision=settings.groq_vision,
            structured_output=settings.groq_structured_output,
            timeout_s=settings.provider_timeout_s,
            client=client,
        )
