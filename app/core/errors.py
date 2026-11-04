"""Typed application errors shared across core and adapter boundaries."""

from __future__ import annotations

from typing import ClassVar


class AppError(Exception):
    """Base class for expected, safe-to-handle application failures."""

    code: ClassVar[str] = "application_error"
    retryable: ClassVar[bool] = False

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class UnsupportedInputError(AppError):
    code = "unsupported_input"


class DocumentLoadError(AppError):
    code = "document_load_failed"


class ProviderError(AppError):
    """Base class for provider failures."""

    code = "provider_error"

    def __init__(
        self,
        message: str,
        *,
        retry_after_s: float | None = None,
        attempts: int = 1,
        retries: int = 0,
        latency_s: float = 0,
    ) -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s
        self.attempts = attempts
        self.retries = retries
        self.latency_s = latency_s


class ProviderRateLimitError(ProviderError):
    code = "provider_rate_limit"
    retryable = True


class ProviderTimeoutError(ProviderError):
    code = "provider_timeout"
    retryable = True


class ProviderServerError(ProviderError):
    code = "provider_server_error"
    retryable = True


class ProviderAuthError(ProviderError):
    code = "provider_auth"


class ProviderCapabilityError(ProviderError):
    code = "provider_capability"


class ProviderInvalidResponseError(ProviderError):
    code = "provider_invalid_response"


class ValidationFailure(AppError):
    code = "validation_failure"


class ConfigError(AppError):
    code = "config_error"
