from pathlib import Path

import pytest
from app.core.errors import ConfigError
from app.domains.registry import DomainProfileRegistry


def test_domain_registry_loads_profiles_and_defaults_to_generic() -> None:
    registry = DomainProfileRegistry()

    assert [profile.id for profile in registry.list_profiles()] == [
        "generic",
        "research_paper",
        "tax_form",
    ]
    assert registry.get_profile().id == "generic"
    assert registry.get_profile("tax_form").id == "tax_form"

    with pytest.raises(ConfigError, match="Unknown domain profile"):
        registry.get_profile("unknown")


def test_domain_registry_rejects_invalid_profile_files(tmp_path: Path) -> None:
    (tmp_path / "generic.yaml").write_text("id: generic\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="Invalid domain profile file"):
        DomainProfileRegistry(tmp_path)


def test_domain_registry_requires_generic_profile(tmp_path: Path) -> None:
    (tmp_path / "research.yaml").write_text(
        "id: research\nname: Research\ndescription: Test\ndefault_instructions: Extract.\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="The required generic domain profile was not found"):
        DomainProfileRegistry(tmp_path)
