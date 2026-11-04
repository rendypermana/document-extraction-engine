"""Deterministic provider adapter for offline integration tests and local demos."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.core.errors import ProviderError
from app.core.schemas import (
    GenerationRequest,
    GenerationResponse,
    ProviderCapabilities,
)


class FakeProvider:
    """Return configured responses or an empty, valid page result deterministically."""

    name = "fake"
    capabilities = ProviderCapabilities(
        vision=True,
        structured_output=True,
        max_image_pixels=None,
        max_input_tokens=None,
        reports_usage=False,
    )

    def __init__(
        self,
        responses: Sequence[str] = (),
        fail_on_calls: Mapping[int, ProviderError] | None = None,
    ) -> None:
        self._responses = tuple(responses)
        self._fail_on_calls = dict(fail_on_calls or {})
        self.call_count = 0

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.call_count += 1
        failure = self._fail_on_calls.get(self.call_count)
        if failure is not None:
            raise failure

        if self.call_count <= len(self._responses):
            text = self._responses[self.call_count - 1]
        else:
            text = f'{{"page": {self.call_count}, "items": []}}'

        return GenerationResponse(
            text=text,
            usage=None,
            model="fake-deterministic",
            latency_s=0,
        )
