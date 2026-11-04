"""Application settings loaded from environment variables or a local .env file."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    provider: str = Field(default="fake", min_length=1)
    gemini_api_key: SecretStr | None = None
    model_name: str = Field(default="gemini-2.5-flash", min_length=1)
    openrouter_api_key: SecretStr | None = None
    openrouter_model: str = ""
    openrouter_vision: bool = False
    openrouter_structured_output: bool = False
    groq_api_key: SecretStr | None = None
    groq_model: str = ""
    groq_vision: bool = False
    groq_structured_output: bool = False

    max_concurrency: int = Field(default=2, ge=1)
    requests_per_minute: int = Field(default=15, ge=1)
    max_retries: int = Field(default=3, ge=0)
    provider_timeout_s: float = Field(default=60, gt=0)

    render_dpi: int = Field(default=150, ge=1)
    ocr_enabled: bool = True
    ocr_language: str = Field(default="eng", min_length=3)
    max_upload_mb: int = Field(default=20, ge=1)
    max_image_pixels: int = Field(default=40_000_000, ge=1)
    max_instruction_chars: int = Field(default=10_000, ge=1)
    max_active_runs: int = Field(default=4, ge=1)
    run_ttl_minutes: int = Field(default=60, ge=1)
    max_stored_runs: int = Field(default=100, ge=1)

    host: str = Field(default="0.0.0.0", min_length=1)
    port: int = Field(default=8000, ge=1, le=65535)

    @property
    def provider_key_configured(self) -> bool:
        """Return whether the configured provider's credential is available."""
        if self.provider != "gemini":
            if self.provider == "openrouter":
                return self._has_value(self.openrouter_api_key) and bool(
                    self.openrouter_model.strip()
                )
            if self.provider == "groq":
                return self._has_value(self.groq_api_key) and bool(self.groq_model.strip())
            return self.provider == "fake"
        return self._has_value(self.gemini_api_key)

    @staticmethod
    def _has_value(secret: SecretStr | None) -> bool:
        return bool(secret and secret.get_secret_value().strip())


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance."""
    return Settings()
