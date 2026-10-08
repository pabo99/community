"""Shared helpers for authentication integration tests.

The AuthService commits internally. To keep tests isolated, the session is
bound to a connection running an outer transaction with
``join_transaction_mode="create_savepoint"``: the service's ``commit()`` only
releases a savepoint, and the outer transaction is rolled back after the test.
"""

from __future__ import annotations

from collections.abc import Iterator

from app.api.auth import get_github_oauth_client
from app.config import Settings, get_settings
from app.db.session import get_db
from app.integrations.github.oauth import GitHubUser
from app.main import create_app
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session


class FakeGitHubOAuthClient:
    """Deterministic stand-in for GitHubOAuthClient (no network)."""

    def __init__(self, user: GitHubUser) -> None:
        self._user = user
        self.exchanged_codes: list[str] = []

    def authorize_url(self, state: str) -> str:
        return f"https://github.test/authorize?state={state}"

    def exchange_code(self, code: str) -> str:
        self.exchanged_codes.append(code)
        return "fake-access-token"

    def fetch_user(self, access_token: str) -> GitHubUser:
        return self._user


def make_auth_settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://unused",
        github_oauth_client_id="cid",
        github_oauth_client_secret="secret",
        session_ttl_seconds=3600,
        oauth_state_ttl_seconds=600,
    )


def build_client(
    migrated_engine: Engine,
    settings: Settings,
    github_user: GitHubUser,
) -> Iterator[tuple[TestClient, Session, FakeGitHubOAuthClient]]:
    """Build a TestClient wired to a savepoint-isolated session + fake GitHub."""
    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    fake_github = FakeGitHubOAuthClient(github_user)
    app = create_app(settings)

    def override_get_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_github_oauth_client] = lambda: fake_github

    client = TestClient(app)
    try:
        yield client, session, fake_github
    finally:
        client.close()
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
