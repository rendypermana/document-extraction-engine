"""OpenRouter adapter using its OpenAI-compatible Chat Completions API."""

from __future__ import annotations

import httpx

from app.config import Settings
from app.core.errors import ConfigError
from app.providers.openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """Call OpenRouter with a user-selected model and model-specific capabilities."""

    name = "openrouter"
    endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        api_key = (
            settings.openrouter_api_key.get_secret_value() if settings.openrouter_api_key else ""
        )
        if not api_key.strip():
            raise ConfigError("OPENROUTER_API_KEY must be configured to use OpenRouter.")
        if not settings.openrouter_model.strip():
            raise ConfigError("OPENROUTER_MODEL must be configured to use OpenRouter.")
        super().__init__(
            name=self.name,
            label="OpenRouter",
            endpoint=self.endpoint,
            api_key=api_key,
            model=settings.openrouter_model.strip(),
            vision=settings.openrouter_vision,
            structured_output=settings.openrouter_structured_output,
            timeout_s=settings.provider_timeout_s,
            client=client,
        )
