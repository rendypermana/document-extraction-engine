import asyncio

import pytest
from app.config import Settings
from app.core.errors import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderServerError,
    ProviderTimeoutError,
)
from app.core.resilience import ResilientProvider
from app.core.schemas import GenerationRequest, GenerationResponse
from app.providers.fake import FakeProvider


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    async def sleep(self, duration: float) -> None:
        self.sleeps.append(duration)
        self.now += duration


def _request() -> GenerationRequest:
    return GenerationRequest(system_prompt="system", user_prompt="user")


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "max_concurrency": 4,
        "requests_per_minute": 1000,
        "max_retries": 2,
        "provider_timeout_s": 1,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_retry_records_attempts_latency_and_retry_after() -> None:
    clock = _Clock()
    provider = FakeProvider(
        responses=["unused", "valid response"],
        fail_on_calls={1: ProviderRateLimitError("quota", retry_after_s=2)},
    )
    resilient = ResilientProvider(
        provider,
        _settings(max_retries=1),
        sleep=clock.sleep,
        clock=clock.monotonic,
    )

    response = asyncio.run(resilient.generate(_request()))

    assert response.text == "valid response"
    assert response.attempts == 2
    assert response.retries == 1
    assert response.latency_s == 2
    assert clock.sleeps == [2]


def test_retry_exhaustion_exposes_safe_metrics() -> None:
    clock = _Clock()
    provider = FakeProvider(
        fail_on_calls={
            1: ProviderServerError("temporary failure"),
            2: ProviderServerError("temporary failure"),
        }
    )
    resilient = ResilientProvider(
        provider,
        _settings(max_retries=1),
        sleep=clock.sleep,
        clock=clock.monotonic,
        random_fraction=lambda: 0.5,
    )

    with pytest.raises(ProviderServerError) as raised:
        asyncio.run(resilient.generate(_request()))

    assert raised.value.attempts == 2
    assert raised.value.retries == 1
    assert raised.value.latency_s == pytest.approx(0.25)
    assert clock.sleeps == [0.25]


def test_permanent_auth_error_is_not_retried() -> None:
    provider = FakeProvider(fail_on_calls={1: ProviderAuthError("credentials rejected")})
    resilient = ResilientProvider(provider, _settings())

    with pytest.raises(ProviderAuthError) as raised:
        asyncio.run(resilient.generate(_request()))

    assert provider.call_count == 1
    assert raised.value.attempts == 1
    assert raised.value.retries == 0


def test_provider_timeout_is_bounded_and_reported() -> None:
    class SlowProvider(FakeProvider):
        async def generate(self, request: GenerationRequest) -> GenerationResponse:
            await asyncio.sleep(0.05)
            return await super().generate(request)

    provider = SlowProvider()
    resilient = ResilientProvider(
        provider,
        _settings(max_retries=0, provider_timeout_s=0.001),
    )

    with pytest.raises(ProviderTimeoutError) as raised:
        asyncio.run(resilient.generate(_request()))

    assert raised.value.attempts == 1
    assert raised.value.retries == 0
    assert provider.call_count == 0


def test_provider_timeout_is_retried_with_a_finite_limit() -> None:
    class SlowOnceProvider(FakeProvider):
        calls = 0

        async def generate(self, request: GenerationRequest) -> GenerationResponse:
            self.calls += 1
            if self.calls == 1:
                await asyncio.sleep(0.05)
            return GenerationResponse(text="ok", model="test", latency_s=0.01)

    provider = SlowOnceProvider()
    resilient = ResilientProvider(
        provider,
        _settings(max_retries=1, provider_timeout_s=0.001),
        random_fraction=lambda: 0,
    )

    response = asyncio.run(resilient.generate(_request()))

    assert response.text == "ok"
    assert response.attempts == 2
    assert response.retries == 1
    assert provider.calls == 2


def test_rate_limiter_enforces_requests_per_minute() -> None:
    clock = _Clock()
    provider = FakeProvider(responses=["first", "second"])
    resilient = ResilientProvider(
        provider,
        _settings(requests_per_minute=1),
        sleep=clock.sleep,
        clock=clock.monotonic,
    )

    async def run_two() -> list[GenerationResponse]:
        return list(
            await asyncio.gather(resilient.generate(_request()), resilient.generate(_request()))
        )

    responses = asyncio.run(run_two())

    assert [response.text for response in responses] == ["first", "second"]
    assert clock.sleeps == [60]


def test_concurrency_is_bounded() -> None:
    class ConcurrentProvider(FakeProvider):
        active = 0
        maximum_active = 0

        async def generate(self, request: GenerationRequest) -> GenerationResponse:
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
            await asyncio.sleep(0.01)
            self.active -= 1
            return GenerationResponse(text="ok", model="test", latency_s=0.01)

    provider = ConcurrentProvider()
    resilient = ResilientProvider(
        provider,
        _settings(max_concurrency=2),
    )

    async def run_many() -> None:
        await asyncio.gather(*(resilient.generate(_request()) for _ in range(8)))

    asyncio.run(run_many())

    assert provider.maximum_active == 2
