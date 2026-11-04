import ast
from pathlib import Path

import pytest
from app.config import Settings
from app.core.errors import (
    ConfigError,
    DocumentLoadError,
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    UnsupportedInputError,
)
from app.core.schemas import (
    GenerationRequest,
    ImagePart,
    ModelPageOutput,
)
from pydantic import ValidationError


def _model_item(item_type: str, content: dict[str, object]) -> dict[str, object]:
    return {
        "type": item_type,
        "status": "ok",
        "is_estimate": False,
        "evidence": [],
        "content": content,
    }


@pytest.mark.parametrize(
    ("item_type", "content"),
    [
        ("prose", {"text": "Result"}),
        (
            "table",
            {
                "columns": [{"path": ["Group", "Mean"]}],
                "rows": [{"cells": [{"value": "4.2"}]}],
            },
        ),
        (
            "chart",
            {
                "chart_type": "bar",
                "series": [
                    {"points": [{"value": "42", "is_estimate": True, "status": "uncertain"}]}
                ],
            },
        ),
        (
            "form_field",
            {"label": "Consent", "field_type": "checkbox", "checked": True},
        ),
    ],
)
def test_model_page_output_accepts_each_discriminated_item(item_type, content) -> None:
    output = ModelPageOutput.model_validate({"page": 1, "items": [_model_item(item_type, content)]})

    assert output.items[0].type == item_type


def test_model_output_ignores_backend_owned_fields() -> None:
    output = ModelPageOutput.model_validate(
        {
            "page": 1,
            "items": [
                {
                    **_model_item("prose", {"text": "Result"}),
                    "id": "untrusted-id",
                    "verified": True,
                    "findings": [{"code": "untrusted"}],
                }
            ],
        }
    )

    assert "id" not in output.items[0].model_dump()
    assert "verified" not in output.items[0].model_dump()
    assert "findings" not in output.items[0].model_dump()


def test_bbox_shape_is_hard_but_bounds_are_left_for_semantic_validation() -> None:
    output = ModelPageOutput.model_validate(
        {
            "page": 1,
            "items": [
                _model_item(
                    "prose",
                    {"text": "Result"},
                )
            ],
        }
    )
    assert output.page == 1

    evidence = {
        "page": 1,
        "excerpt": "Result",
        "bbox": [-0.1, 0.1, 1.1, 0.8],
    }
    output = ModelPageOutput.model_validate(
        {
            "page": 1,
            "items": [
                {
                    **_model_item("prose", {"text": "Result"}),
                    "evidence": [evidence],
                }
            ],
        }
    )
    assert output.items[0].evidence[0].bbox == (-0.1, 0.1, 1.1, 0.8)

    evidence["bbox"] = [0.1, 0.2, 0.9]
    with pytest.raises(ValidationError):
        ModelPageOutput.model_validate(
            {
                "page": 1,
                "items": [
                    {
                        **_model_item("prose", {"text": "Result"}),
                        "evidence": [evidence],
                    }
                ],
            }
        )


def test_generated_model_schema_exposes_discriminator_and_no_backend_fields() -> None:
    schema = ModelPageOutput.model_json_schema()
    serialized = str(schema)

    assert "discriminator" in serialized
    assert "verified" not in serialized
    assert "findings" not in serialized


def test_generation_request_uses_independent_empty_image_lists() -> None:
    first = GenerationRequest(system_prompt="system", user_prompt="user")
    second = GenerationRequest(system_prompt="system", user_prompt="user")

    first.images.append(ImagePart(data=b"image", mime="image/png"))
    assert second.images == []


def test_settings_defaults_match_env_example(monkeypatch) -> None:
    for key in (
        "PROVIDER",
        "GEMINI_API_KEY",
        "MODEL_NAME",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENROUTER_VISION",
        "OPENROUTER_STRUCTURED_OUTPUT",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "GROQ_VISION",
        "GROQ_STRUCTURED_OUTPUT",
        "MAX_CONCURRENCY",
        "REQUESTS_PER_MINUTE",
        "MAX_RETRIES",
        "PROVIDER_TIMEOUT_S",
        "RENDER_DPI",
        "MAX_UPLOAD_MB",
        "MAX_IMAGE_PIXELS",
        "HOST",
        "PORT",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None)

    assert settings.provider == "fake"
    assert settings.gemini_api_key is None
    assert settings.openrouter_api_key is None
    assert settings.openrouter_model == ""
    assert not settings.openrouter_vision
    assert not settings.openrouter_structured_output
    assert settings.groq_api_key is None
    assert settings.groq_model == ""
    assert not settings.groq_vision
    assert not settings.groq_structured_output
    assert settings.model_name == "gemini-2.5-flash"
    assert settings.max_concurrency == 2
    assert settings.requests_per_minute == 15
    assert settings.max_retries == 3
    assert settings.provider_timeout_s == 60
    assert settings.render_dpi == 150
    assert settings.ocr_enabled
    assert settings.ocr_language == "eng"
    assert settings.max_upload_mb == 20
    assert settings.max_image_pixels == 40_000_000
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.provider_key_configured


def test_settings_reject_invalid_operational_bounds() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_concurrency=0)

    with pytest.raises(ValidationError):
        Settings(_env_file=None, provider_timeout_s=0)

    with pytest.raises(ValidationError):
        Settings(_env_file=None, port=65_536)


def test_gemini_availability_does_not_expose_secret() -> None:
    missing_key = Settings(_env_file=None, provider="gemini")
    configured_key = Settings(
        _env_file=None,
        provider="gemini",
        gemini_api_key="test-secret",
    )

    assert not missing_key.provider_key_configured
    assert configured_key.provider_key_configured
    assert "test-secret" not in repr(configured_key)


@pytest.mark.parametrize(
    ("provider", "settings"),
    [
        ("openrouter", {"openrouter_api_key": "test-key", "openrouter_model": "org/model"}),
        ("groq", {"groq_api_key": "test-key", "groq_model": "model-id"}),
    ],
)
def test_compatible_provider_requires_key_and_model(provider, settings) -> None:
    assert not Settings(_env_file=None, provider=provider).provider_key_configured
    assert Settings(_env_file=None, provider=provider, **settings).provider_key_configured
    assert "test-key" not in repr(Settings(_env_file=None, provider=provider, **settings))


@pytest.mark.parametrize(
    ("error_type", "code", "retryable"),
    [
        (UnsupportedInputError, "unsupported_input", False),
        (DocumentLoadError, "document_load_failed", False),
        (ProviderAuthError, "provider_auth", False),
        (ProviderRateLimitError, "provider_rate_limit", True),
        (ProviderTimeoutError, "provider_timeout", True),
        (ConfigError, "config_error", False),
    ],
)
def test_typed_errors_expose_stable_code_and_retryability(error_type, code, retryable) -> None:
    error = error_type("safe message")

    assert str(error) == "safe message"
    assert error.code == code
    assert error.retryable is retryable


def test_provider_sdk_imports_are_confined_to_provider_adapters() -> None:
    app_root = Path(__file__).parents[1] / "app"
    provider_root = app_root / "providers"
    provider_sdks = ("google.genai", "google.generativeai")

    for source_path in app_root.rglob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules = [node.module]
            else:
                continue

            imports_provider_sdk = any(
                module == sdk or module.startswith(f"{sdk}.")
                for module in imported_modules
                for sdk in provider_sdks
            )
            if imports_provider_sdk:
                assert source_path.is_relative_to(provider_root), source_path
