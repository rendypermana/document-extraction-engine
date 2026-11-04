"""Google Gemini adapter; provider-specific SDK behavior stays in this module."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import Settings
from app.core.errors import (
    ConfigError,
    ProviderAuthError,
    ProviderCapabilityError,
    ProviderError,
    ProviderInvalidResponseError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderTimeoutError,
)
from app.core.schemas import (
    GenerationRequest,
    GenerationResponse,
    ProviderCapabilities,
    Usage,
)


class GeminiProvider:
    """Translate shared generation requests to the asynchronous Gemini SDK."""

    name = "gemini"
    capabilities = ProviderCapabilities(
        vision=True,
        structured_output=True,
        max_image_pixels=None,
        max_input_tokens=None,
        reports_usage=True,
    )

    def __init__(self, settings: Settings, client: genai.Client | None = None) -> None:
        self._model = settings.model_name
        if client is None:
            api_key = settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else ""
            if not api_key.strip():
                raise ConfigError("GEMINI_API_KEY must be configured to use Gemini.")
            client = genai.Client(api_key=api_key)
        self._client = client

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        parts = [types.Part.from_text(text=request.user_prompt)]
        parts.extend(
            types.Part.from_bytes(data=image.data, mime_type=image.mime) for image in request.images
        )
        contents = types.Content(role="user", parts=parts)
        config = types.GenerateContentConfig(
            system_instruction=request.system_prompt,
            response_mime_type="application/json",
            response_json_schema=request.response_schema,
        )
        started = time.perf_counter()
        try:
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
        except genai_errors.APIError as error:
            raise self._map_api_error(error) from error
        except httpx.TimeoutException as error:
            raise ProviderTimeoutError("The Gemini request timed out.") from error
        except httpx.NetworkError as error:
            raise ProviderServerError("The Gemini service could not be reached.") from error

        try:
            text = response.text
        except ValueError as error:
            raise ProviderInvalidResponseError("Gemini did not return a text response.") from error
        if not isinstance(text, str) or not text.strip():
            raise ProviderInvalidResponseError("Gemini did not return a text response.")

        usage_metadata = response.usage_metadata
        usage = None
        if usage_metadata is not None and (
            usage_metadata.prompt_token_count is not None
            or usage_metadata.candidates_token_count is not None
        ):
            usage = Usage(
                input_tokens=usage_metadata.prompt_token_count,
                output_tokens=usage_metadata.candidates_token_count,
            )

        return GenerationResponse(
            text=text,
            usage=usage,
            model=response.model_version or self._model,
            latency_s=max(0.0, time.perf_counter() - started),
        )

    @classmethod
    def _map_api_error(cls, error: genai_errors.APIError) -> ProviderError:
        status_code = error.code
        if status_code == 429:
            return ProviderRateLimitError(
                "The Gemini request rate limit has been reached.",
                retry_after_s=cls._retry_after_seconds(error),
            )
        if status_code in {401, 403}:
            return ProviderAuthError("Gemini rejected the configured credentials.")
        if status_code in {408, 504}:
            return ProviderTimeoutError("The Gemini request timed out.")
        if status_code >= 500:
            return ProviderServerError("The Gemini service encountered an error.")
        if status_code == 404:
            return ProviderCapabilityError(
                "Gemini returned HTTP 404; check model availability and access permissions."
            )
        if status_code in {400, 413, 415, 422}:
            return ProviderCapabilityError(
                f"Gemini returned HTTP {status_code}; check the request schema "
                "and model capabilities."
            )
        return ProviderError("The Gemini request failed.")

    @staticmethod
    def _retry_after_seconds(error: genai_errors.APIError) -> float | None:
        response = error.response
        headers = getattr(response, "headers", None)
        if headers is None:
            return None

        header_value = headers.get("Retry-After")
        if not header_value:
            return None

        try:
            delay = float(header_value)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(header_value)
            except (TypeError, ValueError, OverflowError):
                return None
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            delay = (retry_at - datetime.now(UTC)).total_seconds()
        return max(0.0, delay)
