import asyncio
from types import SimpleNamespace

import httpx
import pytest
from app.config import Settings
from app.core.errors import (
    ConfigError,
    ProviderAuthError,
    ProviderCapabilityError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderTimeoutError,
)
from app.core.schemas import GenerationRequest, ImagePart, ModelPageOutput
from app.providers.gemini import GeminiProvider
from google.genai import errors as genai_errors


class _FakeModels:
    def __init__(self, response: object | Exception) -> None:
        self.response = response
        self.kwargs: dict[str, object] | None = None

    async def generate_content(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _provider(response: object | Exception) -> tuple[GeminiProvider, _FakeModels]:
    models = _FakeModels(response)
    client = SimpleNamespace(aio=SimpleNamespace(models=models))
    settings = Settings(
        _env_file=None,
        provider="gemini",
        model_name="test-model",
        gemini_api_key="secret-test-key",
    )
    return GeminiProvider(settings, client=client), models


def test_gemini_adapter_builds_structured_multimodal_request_and_maps_usage() -> None:
    response = SimpleNamespace(
        text='{"page":1,"items":[]}',
        usage_metadata=SimpleNamespace(prompt_token_count=12, candidates_token_count=4),
        model_version="test-model-version",
    )
    provider, models = _provider(response)
    request = GenerationRequest(
        system_prompt="system",
        user_prompt="user",
        images=[ImagePart(data=b"image-bytes", mime="image/png")],
        response_schema=ModelPageOutput.model_json_schema(),
    )

    generated = asyncio.run(provider.generate(request))

    assert generated.text == response.text
    assert generated.model == "test-model-version"
    assert generated.usage is not None
    assert generated.usage.input_tokens == 12
    assert generated.usage.output_tokens == 4
    assert models.kwargs is not None
    assert models.kwargs["model"] == "test-model"
    config = models.kwargs["config"]
    assert config.system_instruction == "system"
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == ModelPageOutput.model_json_schema()
    content = models.kwargs["contents"]
    assert content.parts[0].text == "user"
    assert content.parts[1].inline_data.data == b"image-bytes"


def test_gemini_adapter_records_usage_as_unavailable_when_not_returned() -> None:
    provider, _ = _provider(
        SimpleNamespace(text='{"page":1,"items":[]}', usage_metadata=None, model_version=None)
    )

    response = asyncio.run(provider.generate(GenerationRequest(system_prompt="s", user_prompt="u")))

    assert response.usage is None
    assert response.model == "test-model"


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (401, ProviderAuthError),
        (403, ProviderAuthError),
        (429, ProviderRateLimitError),
        (408, ProviderTimeoutError),
        (500, ProviderServerError),
        (503, ProviderServerError),
        (404, ProviderCapabilityError),
    ],
)
def test_gemini_api_errors_are_classified_without_exposing_sdk_message(
    status_code: int,
    expected_error: type[Exception],
) -> None:
    sdk_error = genai_errors.ClientError(
        status_code,
        {"message": "secret-test-key must never be shown"},
        httpx.Response(status_code),
    )
    provider, _ = _provider(sdk_error)

    with pytest.raises(expected_error) as raised:
        asyncio.run(provider.generate(GenerationRequest(system_prompt="s", user_prompt="u")))

    assert "secret-test-key" not in str(raised.value)
    if status_code == 404:
        assert "HTTP 404" in str(raised.value)
        assert "model availability" in str(raised.value)


def test_gemini_rate_limit_preserves_retry_after_header() -> None:
    sdk_error = genai_errors.ClientError(
        429,
        {"message": "rate limited"},
        httpx.Response(429, headers={"Retry-After": "3"}),
    )
    provider, _ = _provider(sdk_error)

    with pytest.raises(ProviderRateLimitError) as raised:
        asyncio.run(provider.generate(GenerationRequest(system_prompt="s", user_prompt="u")))

    assert raised.value.retry_after_s == 3


def test_gemini_requires_key_when_client_is_not_injected() -> None:
    with pytest.raises(ConfigError, match="GEMINI_API_KEY"):
        GeminiProvider(Settings(_env_file=None, provider="gemini"))
