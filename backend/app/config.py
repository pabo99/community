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

    # --- GitHub OAuth / sessions -------------------------------------------
    # These are OPTIONAL for normal startup (health, non-auth routes work
    # without them). Authentication fails closed with a clear, sanitized error
    # when attempted without the required credentials (see auth config check).
    github_oauth_client_id: str | None = None
    github_oauth_client_secret: str | None = None
    # Backend callback URL registered with the GitHub OAuth App.
    github_oauth_redirect_uri: str = "http://localhost:5173/api/auth/github/callback"
    # Minimal scope: read the authenticated user's public profile.
    github_oauth_scope: str = "read:user"

    # Trusted destination the browser is sent to after login/logout. Never
    # taken from a request parameter.
    frontend_post_login_url: str = "/"

    # Opaque session cookie configuration.
    session_cookie_name: str = "community_session"
    # Absolute session lifetime in seconds (default 14 days).
    session_ttl_seconds: int = 14 * 24 * 60 * 60
    # Short-lived OAuth state lifetime in seconds.
    oauth_state_ttl_seconds: int = 10 * 60
    # CSRF cookie (double-submit) name; readable by JS so the SPA can echo it.
    csrf_cookie_name: str = "community_csrf"
    csrf_header_name: str = "X-CSRF-Token"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def docs_enabled(self) -> bool:
        """OpenAPI docs are served outside production."""
        return self.environment.lower() != "production"

    @property
    def cookie_secure(self) -> bool:
        """Cookies are Secure in production; relaxed for local HTTP dev."""
        return self.is_production

    @property
    def github_oauth_configured(self) -> bool:
        return bool(self.github_oauth_client_id and self.github_oauth_client_secret)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    # Required fields (e.g. database_url) are populated from the environment.
    return Settings()  # type: ignore[call-arg]
