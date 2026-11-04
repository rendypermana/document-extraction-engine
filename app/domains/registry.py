"""Discover and validate YAML domain profiles."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.core.errors import ConfigError
from app.core.schemas import DomainProfile


class DomainProfileRegistry:
    """Load domain profiles once and provide stable lookup by ID."""

    def __init__(self, directory: Path | None = None) -> None:
        self._directory = directory or Path(__file__).parent
        self._profiles = self._load_profiles()

    def list_profiles(self) -> list[DomainProfile]:
        """Return profiles ordered by their IDs."""
        return [self._profiles[key] for key in sorted(self._profiles)]

    def get_profile(self, profile_id: str | None = None) -> DomainProfile:
        """Return a profile, defaulting to the required generic profile."""
        selected_id = "generic" if profile_id is None else profile_id
        try:
            return self._profiles[selected_id]
        except KeyError as error:
            raise ConfigError(f"Unknown domain profile: {selected_id}") from error

    def _load_profiles(self) -> dict[str, DomainProfile]:
        paths = sorted(self._directory.glob("*.yaml"))
        if not paths:
            raise ConfigError(f"No domain profiles were found in {self._directory}.")

        profiles: dict[str, DomainProfile] = {}
        for path in paths:
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                profile = DomainProfile.model_validate(data)
            except (OSError, UnicodeError, yaml.YAMLError, ValidationError) as error:
                raise ConfigError(f"Invalid domain profile file: {path.name}") from error

            if profile.id in profiles:
                raise ConfigError(f"ID profil domain duplikat: {profile.id}")
            profiles[profile.id] = profile

        if "generic" not in profiles:
            raise ConfigError("The required generic domain profile was not found.")
        return profiles
