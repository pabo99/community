"""Application configuration.

Deployment configuration is provided through environment variables
(technical-design.md §10). The production ``Settings`` model intentionally
contains only configuration that the backend needs at this milestone. Database
configuration is introduced in M1-03; external integrations later.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend runtime settings loaded from the environment.

    Every field here has a safe development default, so the application can
    start in local development without extra configuration. Fields become
    required (no default) only when the backend genuinely cannot run without
    them; none do yet at M1-02.
    """

    model_config = SettingsConfigDict(
        env_file=None,
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "development"
    api_title: str = "Community Platform API"
    api_version: str = "0.1.0"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    @property
    def docs_enabled(self) -> bool:
        """OpenAPI docs are served outside production."""
        return self.environment.lower() != "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
