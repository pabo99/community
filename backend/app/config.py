"""Application configuration.

Deployment configuration is provided through environment variables
(technical-design.md §10). The production ``Settings`` model intentionally
contains only configuration that the backend needs at this milestone.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Backend runtime settings loaded from the environment.

    Most fields have safe development defaults. ``database_url`` is required
    (no default): the backend genuinely cannot run its persistence paths
    without it, and we do not ship a production database default
    (technical-design.md §10).
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

    # Required: the SQLAlchemy/psycopg connection URL, e.g.
    # postgresql+psycopg://user:pass@db:5432/community. No default is provided.
    database_url: str

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
    # Required fields (e.g. database_url) are populated from the environment.
    return Settings()  # type: ignore[call-arg]
