import asyncio
import base64
import json

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
from app.providers.groq import GroqProvider
from app.providers.openrouter import OpenRouterProvider


def _settings(provider: str, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "provider": provider,
        "openrouter_api_key": "openrouter-test-secret",
        "openrouter_model": "openai/gpt-oss-20b",
        "groq_api_key": "groq-test-secret",
        "groq_model": "openai/gpt-oss-20b",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def _handler(response_data: object, status_code: int = 200, headers: dict | None = None):
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status_code, headers=headers, json=response_data)

    return httpx.MockTransport(handle), seen


@pytest.mark.parametrize(
    ("provider_cls", "provider", "endpoint", "key_header"),
    [
        (
            OpenRouterProvider,
            "openrouter",
            "https://openrouter.ai/api/v1/chat/completions",
            "Bearer openrouter-test-secret",
        ),
        (
            GroqProvider,
            "groq",
            "https://api.groq.com/openai/v1/chat/completions",
            "Bearer groq-test-secret",
        ),
    ],
)
def test_compatible_provider_sends_chat_request_and_parses_usage(
    provider_cls,
    provider: str,
    endpoint: str,
    key_header: str,
) -> None:
    transport, seen = _handler(
        {
            "model": "actual-model",
            "choices": [{"message": {"content": '{"page":1,"items":[]}'}}],
            "usage": {"prompt_tokens": 23, "completion_tokens": 5},
        }
    )
    settings = _settings(
        provider,
        **{
            f"{provider}_vision": True,
            f"{provider}_structured_output": True,
        },
    )

    async def run() -> object:
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = provider_cls(settings, client=client)
            return await adapter.generate(
                GenerationRequest(
                    system_prompt="system instructions",
                    user_prompt="extract values",
                    images=[ImagePart(data=b"image-data", mime="image/png")],
                    response_schema=ModelPageOutput.model_json_schema(),
                )
            )

    response = asyncio.run(run())
    sent = seen[0]
    payload = json.loads(sent.content)
    image_part = payload["messages"][1]["content"][1]

    assert str(sent.url) == endpoint
    assert sent.headers["Authorization"] == key_header
    expected_model = settings.openrouter_model if provider == "openrouter" else settings.groq_model
    assert payload["model"] == expected_model
    assert payload["temperature"] == 0
    assert payload["messages"][0] == {"role": "system", "content": "system instructions"}
    assert payload["messages"][1]["content"][0] == {
        "type": "text",
        "text": "extract values",
    }
    assert image_part["type"] == "image_url"
    assert image_part["image_url"]["url"] == (
        "data:image/png;base64," + base64.b64encode(b"image-data").decode("ascii")
    )
    assert payload["response_format"]["type"] == "json_schema"
    assert payload["response_format"]["json_schema"]["strict"] is False
    assert response.text == '{"page":1,"items":[]}'
    assert response.model == "actual-model"
    assert response.usage is not None
    assert response.usage.input_tokens == 23
    assert response.usage.output_tokens == 5


@pytest.mark.parametrize(
    ("provider_cls", "provider"),
    [(OpenRouterProvider, "openrouter"), (GroqProvider, "groq")],
)
def test_compatible_provider_defaults_to_json_prompt_without_schema_flag(
    provider_cls,
    provider: str,
) -> None:
    transport, seen = _handler(
        {
            "choices": [
                {"message": {"content": [{"type": "text", "text": '{"page":1,"items":[]}'}]}}
            ],
        }
    )

    async def run() -> object:
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = provider_cls(_settings(provider), client=client)
            return await adapter.generate(
                GenerationRequest(
                    system_prompt="system",
                    user_prompt="user",
                    response_schema=ModelPageOutput.model_json_schema(),
                )
            )

    response = asyncio.run(run())
    payload = json.loads(seen[0].content)

    assert "response_format" not in payload
    assert response.text == '{"page":1,"items":[]}'
    assert response.usage is None


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (401, ProviderAuthError),
        (403, ProviderAuthError),
        (429, ProviderRateLimitError),
        (408, ProviderTimeoutError),
        (500, ProviderServerError),
        (502, ProviderServerError),
        (400, ProviderCapabilityError),
        (404, ProviderCapabilityError),
    ],
)
@pytest.mark.parametrize(
    ("provider_cls", "provider", "sentinel"),
    [
        (OpenRouterProvider, "openrouter", "openrouter-test-secret"),
        (GroqProvider, "groq", "groq-test-secret"),
    ],
)
def test_compatible_provider_maps_http_failures_without_leaking_body(
    status_code: int,
    expected_error: type[Exception],
    provider_cls,
    provider: str,
    sentinel: str,
) -> None:
    transport, _ = _handler(
        {"error": {"message": f"unsafe provider detail {sentinel}"}},
        status_code=status_code,
        headers={"Retry-After": "2"},
    )

    async def run() -> None:
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = provider_cls(_settings(provider), client=client)
            await adapter.generate(GenerationRequest(system_prompt="s", user_prompt="u"))

    with pytest.raises(expected_error) as raised:
        asyncio.run(run())

    assert sentinel not in str(raised.value)
    assert sentinel not in repr(raised.value)
    if status_code == 429:
        assert raised.value.retry_after_s == 2


@pytest.mark.parametrize(
    ("provider_cls", "provider", "missing_key_env", "missing_model_env"),
    [
        (OpenRouterProvider, "openrouter", "openrouter_api_key", "openrouter_model"),
        (GroqProvider, "groq", "groq_api_key", "groq_model"),
    ],
)
def test_compatible_provider_requires_key_and_model(
    provider_cls,
    provider: str,
    missing_key_env: str,
    missing_model_env: str,
) -> None:
    with pytest.raises(ConfigError, match="API_KEY"):
        provider_cls(_settings(provider, **{missing_key_env: None}))
    with pytest.raises(ConfigError, match=missing_model_env.upper()):
        provider_cls(_settings(provider, **{missing_model_env: ""}))


@pytest.mark.parametrize(
    ("provider_cls", "provider"),
    [(OpenRouterProvider, "openrouter"), (GroqProvider, "groq")],
)
def test_compatible_provider_maps_network_timeout_to_safe_error(
    provider_cls,
    provider: str,
) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("unsafe network detail with test key")

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            adapter = provider_cls(_settings(provider), client=client)
            await adapter.generate(GenerationRequest(system_prompt="s", user_prompt="u"))

    with pytest.raises(ProviderTimeoutError) as raised:
        asyncio.run(run())

    assert "unsafe network detail" not in str(raised.value)
