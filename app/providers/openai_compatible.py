"""Shared OpenAI Chat Completions transport for compatible provider adapters."""

from __future__ import annotations

import base64
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from app.core.errors import (
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


class OpenAICompatibleProvider:
    """Translate shared generation requests to a chat-completions endpoint."""

    def __init__(
        self,
        *,
        name: str,
        label: str,
        endpoint: str,
        api_key: str,
        model: str,
        vision: bool,
        structured_output: bool,
        timeout_s: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.name = name
        self._label = label
        self._endpoint = endpoint
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s
        self._client = client
        self.capabilities = ProviderCapabilities(
            vision=vision,
            structured_output=structured_output,
            max_image_pixels=None,
            max_input_tokens=None,
            reports_usage=True,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": self._user_content(request)},
            ],
        }
        if self.capabilities.structured_output and request.response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "model_page_output",
                    "strict": False,
                    "schema": request.response_schema,
                },
            }

        started = time.perf_counter()
        try:
            response = await self._post(payload)
        except httpx.TimeoutException:
            raise ProviderTimeoutError(f"The {self._label} request timed out.") from None
        except httpx.NetworkError:
            raise ProviderServerError(f"The {self._label} service could not be reached.") from None

        if response.status_code >= 400:
            raise self._map_http_error(response)

        try:
            data = response.json()
        except ValueError:
            raise ProviderInvalidResponseError(
                f"{self._label} returned an invalid response."
            ) from None

        text = self._extract_text(data)
        usage = self._extract_usage(data)
        model = data.get("model")
        return GenerationResponse(
            text=text,
            usage=usage,
            model=model if isinstance(model, str) and model else self._model,
            latency_s=max(0.0, time.perf_counter() - started),
        )

    async def _post(self, payload: dict[str, Any]) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if self._client is not None:
            return await self._client.post(
                self._endpoint,
                headers=headers,
                json=payload,
                timeout=self._timeout_s,
            )

        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            return await client.post(self._endpoint, headers=headers, json=payload)

    @staticmethod
    def _user_content(request: GenerationRequest) -> str | list[dict[str, Any]]:
        if not request.images:
            return request.user_prompt
        content: list[dict[str, Any]] = [{"type": "text", "text": request.user_prompt}]
        for image in request.images:
            encoded = base64.b64encode(image.data).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{image.mime};base64,{encoded}",
                    },
                }
            )
        return content

    def _map_http_error(self, response: httpx.Response) -> ProviderError:
        status_code = response.status_code
        if status_code == 429:
            return ProviderRateLimitError(
                f"The {self._label} request rate limit has been reached.",
                retry_after_s=self._retry_after_seconds(response),
            )
        if status_code in {401, 403}:
            return ProviderAuthError(f"{self._label} rejected the configured credentials.")
        if status_code in {408, 504}:
            return ProviderTimeoutError(f"The {self._label} request timed out.")
        if status_code >= 500:
            return ProviderServerError(f"The {self._label} service encountered an error.")
        if status_code in {400, 404, 413, 415, 422}:
            return ProviderCapabilityError(
                f"{self._label} returned HTTP {status_code}; check the model "
                "and request capabilities."
            )
        return ProviderError(f"The {self._label} request failed with HTTP {status_code}.")

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float | None:
        header_value = response.headers.get("Retry-After")
        if not header_value:
            return None
        try:
            return max(0.0, float(header_value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(header_value)
            except (TypeError, ValueError, OverflowError):
                return None
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())

    def _extract_text(self, data: Any) -> str:
        if not isinstance(data, dict):
            raise ProviderInvalidResponseError(f"{self._label} returned an invalid response.")
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ProviderInvalidResponseError(f"{self._label} did not return a response choice.")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise ProviderInvalidResponseError(f"{self._label} did not return a response message.")
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content
        if isinstance(content, list):
            text = "".join(
                part["text"]
                for part in content
                if isinstance(part, dict)
                and part.get("type") == "text"
                and isinstance(part.get("text"), str)
            )
            if text.strip():
                return text
        raise ProviderInvalidResponseError(f"{self._label} did not return a text response.")

    @staticmethod
    def _extract_usage(data: Any) -> Usage | None:
        if not isinstance(data, dict):
            return None
        usage = data.get("usage")
        if not isinstance(usage, dict):
            return None
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        if input_tokens is None and output_tokens is None:
            return None
        return Usage(input_tokens=input_tokens, output_tokens=output_tokens)
