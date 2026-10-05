"""Tests for application configuration behavior."""

from __future__ import annotations

import pytest
from app.config import Settings
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


def test_production_settings_start_with_safe_defaults() -> None:
    """The M1-02 production settings require no extra configuration to load."""
    settings = Settings()

    assert settings.environment == "development"
    assert settings.is_development is True
    assert settings.docs_enabled is True


def test_docs_disabled_in_production() -> None:
    settings = Settings(environment="production")

    assert settings.is_development is False
    assert settings.docs_enabled is False


def test_missing_required_setting_raises_clear_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pydantic Settings fails clearly when a genuinely required field is unset.

    This uses a test-only settings model with one required field so we verify
    the failure behavior without introducing an artificial production
    requirement (production ``Settings`` has safe defaults for everything).
    """

    class RequiredSettings(BaseSettings):
        model_config = SettingsConfigDict(env_file=None)

        required_value: str

    monkeypatch.delenv("REQUIRED_VALUE", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        RequiredSettings()  # type: ignore[call-arg]  # required field intentionally unset

    error = exc_info.value
    assert error.error_count() == 1
    assert error.errors()[0]["type"] == "missing"
    assert error.errors()[0]["loc"] == ("required_value",)
