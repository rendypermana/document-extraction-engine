"""Provider-wide timeout, rate limiting, concurrency, and bounded retry policy."""

from __future__ import annotations

import asyncio
import random
import time
from collections import deque
from collections.abc import Awaitable, Callable

from app.config import Settings
from app.core.errors import ProviderError, ProviderTimeoutError
from app.core.interfaces import Provider
from app.core.schemas import GenerationRequest, GenerationResponse

_RATE_WINDOW_S = 60.0
_RETRY_BASE_DELAY_S = 0.5
_RETRY_MAX_DELAY_S = 30.0


class _WindowRateLimiter:
    def __init__(
        self,
        requests_per_minute: int,
        *,
        clock: Callable[[], float],
        sleep: Callable[[float], Awaitable[None]],
    ) -> None:
        self._limit = requests_per_minute
        self._clock = clock
        self._sleep = sleep
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = self._clock()
                while self._timestamps and now - self._timestamps[0] >= _RATE_WINDOW_S:
                    self._timestamps.popleft()

                if len(self._timestamps) < self._limit:
                    self._timestamps.append(now)
                    return

                delay = _RATE_WINDOW_S - (now - self._timestamps[0])

            await self._sleep(delay)


class ResilientProvider:
    """Apply shared request controls around any provider adapter."""

    def __init__(
        self,
        provider: Provider,
        settings: Settings,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        random_fraction: Callable[[], float] = random.random,
    ) -> None:
        self._provider = provider
        self.name = provider.name
        self.capabilities = provider.capabilities
        self._max_retries = settings.max_retries
        self._timeout_s = settings.provider_timeout_s
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)
        self._sleep = sleep
        self._clock = clock
        self._random_fraction = random_fraction
        self._rate_limiter = _WindowRateLimiter(
            settings.requests_per_minute,
            clock=clock,
            sleep=sleep,
        )

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        started = self._clock()
        attempts = 0
        retries = 0

        while True:
            try:
                async with self._semaphore:
                    await self._rate_limiter.acquire()
                    attempts += 1
                    response = await asyncio.wait_for(
                        self._provider.generate(request),
                        timeout=self._timeout_s,
                    )
            except TimeoutError:
                error = ProviderTimeoutError("The provider request timed out.")
            except ProviderError as provider_error:
                error = provider_error
            else:
                return response.model_copy(
                    update={
                        "latency_s": max(0.0, self._clock() - started),
                        "attempts": attempts,
                        "retries": retries,
                        "cached": False,
                    }
                )

            elapsed = max(0.0, self._clock() - started)
            delay = self._retry_delay(error, retries)
            if not error.retryable or retries >= self._max_retries or delay is None:
                raise self._with_metrics(error, attempts, retries, elapsed) from error

            retries += 1
            await self._sleep(delay)

    def _retry_delay(self, error: ProviderError, retries: int) -> float | None:
        if error.retry_after_s is not None:
            delay = error.retry_after_s
            if delay < 0 or delay > _RETRY_MAX_DELAY_S:
                return None
            return delay

        ceiling = min(_RETRY_MAX_DELAY_S, _RETRY_BASE_DELAY_S * (2**retries))
        return ceiling * min(1.0, max(0.0, self._random_fraction()))

    @staticmethod
    def _with_metrics(
        error: ProviderError,
        attempts: int,
        retries: int,
        latency_s: float,
    ) -> ProviderError:
        return type(error)(
            error.message,
            retry_after_s=error.retry_after_s,
            attempts=attempts,
            retries=retries,
            latency_s=latency_s,
        )
