"""Provider construction from application settings."""

from __future__ import annotations

import httpx

from app.config import Settings
from app.core.errors import ConfigError
from app.core.interfaces import Provider
from app.providers.fake import FakeProvider


def create_provider(
    settings: Settings,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> Provider:
    """Create the configured provider without leaking provider choices to core."""
    if settings.provider == "fake":
        return FakeProvider()
    if settings.provider == "gemini":
        from app.providers.gemini import GeminiProvider

        return GeminiProvider(settings)
    if settings.provider == "openrouter":
        from app.providers.openrouter import OpenRouterProvider

        return OpenRouterProvider(settings, client=http_client)
    if settings.provider == "groq":
        from app.providers.groq import GroqProvider

        return GroqProvider(settings, client=http_client)
    raise ConfigError(f"Unknown configured provider: {settings.provider}")
