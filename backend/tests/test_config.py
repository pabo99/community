"""Tests for application configuration behavior.

These are unit tests: they construct ``Settings`` directly and never open a
database connection.
"""

from __future__ import annotations

import pytest
from app.config import Settings
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# A syntactically valid URL used only to satisfy the required field; no
# connection is made in these unit tests.
_DUMMY_DB_URL = "postgresql+psycopg://user:pass@db:5432/community"


def test_settings_load_with_safe_defaults_when_required_config_present() -> None:
    """Non-database fields default safely once required config is supplied."""
    settings = Settings(database_url=_DUMMY_DB_URL)

    assert settings.environment == "development"
    assert settings.is_development is True
    assert settings.docs_enabled is True
    assert settings.database_url == _DUMMY_DB_URL


def test_docs_disabled_in_production() -> None:
    settings = Settings(database_url=_DUMMY_DB_URL, environment="production")

    assert settings.is_development is False
    assert settings.docs_enabled is False


def test_database_url_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """``Settings`` fails clearly when the required DATABASE_URL is unset.

    There is no production default for DATABASE_URL (technical-design.md §10).
    """
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings()  # type: ignore[call-arg]  # required database_url intentionally unset

    error = exc_info.value
    assert any(
        err["type"] == "missing" and err["loc"] == ("database_url",) for err in error.errors()
    )


def test_missing_required_setting_raises_clear_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pydantic Settings fails clearly when a genuinely required field is unset.

    This uses a test-only settings model with one required field to assert the
    generic failure behavior independent of the production model.
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
