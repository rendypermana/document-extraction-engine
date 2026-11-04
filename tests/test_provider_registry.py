import builtins

import pytest
from app.config import Settings
from app.core.errors import ConfigError
from app.providers.fake import FakeProvider
from app.providers.groq import GroqProvider
from app.providers.openrouter import OpenRouterProvider
from app.providers.registry import create_provider


@pytest.mark.parametrize(
    ("provider", "settings", "expected_type"),
    [
        ("fake", {}, FakeProvider),
        (
            "gemini",
            {"gemini_api_key": "test-key"},
            "GeminiProvider",
        ),
        (
            "openrouter",
            {"openrouter_api_key": "test-key", "openrouter_model": "org/model"},
            OpenRouterProvider,
        ),
        (
            "groq",
            {"groq_api_key": "test-key", "groq_model": "model-id"},
            GroqProvider,
        ),
    ],
)
def test_provider_factory_creates_selected_adapter(provider, settings, expected_type) -> None:
    adapter = create_provider(Settings(_env_file=None, provider=provider, **settings))

    if isinstance(expected_type, str):
        assert type(adapter).__name__ == expected_type
    else:
        assert isinstance(adapter, expected_type)


def test_fake_provider_factory_does_not_import_gemini_sdk(monkeypatch) -> None:
    original_import = builtins.__import__

    def reject_gemini_sdk(name, *args, **kwargs):
        if name == "google.genai" or name.startswith("google.genai."):
            raise AssertionError("Fake provider must not import the Gemini SDK.")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_gemini_sdk)

    adapter = create_provider(Settings(_env_file=None, provider="fake"))

    assert isinstance(adapter, FakeProvider)


def test_provider_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ConfigError, match="Unknown configured provider"):
        create_provider(Settings(_env_file=None, provider="unknown"))


@pytest.mark.parametrize(
    ("provider", "settings", "message"),
    [
        ("openrouter", {}, "OPENROUTER_API_KEY"),
        (
            "groq",
            {"groq_api_key": "test-key"},
            "GROQ_MODEL",
        ),
    ],
)
def test_provider_factory_reports_missing_configuration(provider, settings, message) -> None:
    with pytest.raises(ConfigError, match=message):
        create_provider(Settings(_env_file=None, provider=provider, **settings))
