"""Integration tests for the GitHub OAuth login flow and sessions.

Uses a deterministic fake GitHub client (no live calls) and a real PostgreSQL
database. The TestClient follows redirects manually so we can assert status
codes and cookies.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.auth.cookies import OAUTH_BINDING_COOKIE
from app.config import Settings
from app.integrations.github.oauth import GitHubUser
from app.models.external_identity import ExternalIdentity
from app.models.person import Person
from app.models.session import OAuthState, UserSession
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from tests.integration.conftest_auth import build_client, make_auth_settings

pytestmark = pytest.mark.integration

_GH_USER = GitHubUser(id="12345", login="octocat", name="The Octocat")


@pytest.fixture
def auth_settings() -> Settings:
    return make_auth_settings()


@pytest.fixture
def wired(
    migrated_engine: Engine, auth_settings: Settings
) -> Iterator[tuple[TestClient, Session, object]]:
    yield from build_client(migrated_engine, auth_settings, _GH_USER)


def _login_and_get_state(client: TestClient) -> tuple[str, str]:
    """Hit /login, return (state, binding cookie) from the redirect."""
    resp = client.get("/api/auth/github/login", follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["location"]
    state = location.split("state=")[1]
    binding = client.cookies.get(OAUTH_BINDING_COOKIE)
    assert binding
    return state, binding


def test_login_redirects_to_github_and_sets_binding(wired) -> None:  # type: ignore[no-untyped-def]
    client, _session, _gh = wired
    resp = client.get("/api/auth/github/login", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("https://github.test/authorize")
    assert client.cookies.get(OAUTH_BINDING_COOKIE)


def test_full_login_creates_person_identity_and_session(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _gh = wired
    state, _binding = _login_and_get_state(client)

    resp = client.get(f"/api/auth/github/callback?code=abc&state={state}", follow_redirects=False)
    assert resp.status_code == 302
    # Session cookie set; CSRF cookie set.
    assert client.cookies.get("community_session")
    assert client.cookies.get("community_csrf")

    person = session.scalars(select(Person)).one()
    identity = session.scalars(select(ExternalIdentity)).one()
    assert identity.provider == "github"
    assert identity.provider_user_id == "12345"
    assert identity.username == "octocat"
    assert identity.verified_at is not None
    assert person.display_name == "The Octocat"
    assert session.scalars(select(UserSession)).one().person_id == person.id


def test_me_returns_profile_when_authenticated(wired) -> None:  # type: ignore[no-untyped-def]
    client, _session, _gh = wired
    state, _ = _login_and_get_state(client)
    client.get(f"/api/auth/github/callback?code=abc&state={state}", follow_redirects=False)

    resp = client.get("/api/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["github_username"] == "octocat"
    assert body["display_name"] == "The Octocat"


def test_me_401_when_anonymous(wired) -> None:  # type: ignore[no-untyped-def]
    client, _session, _gh = wired
    resp = client.get("/api/me")
    assert resp.status_code == 401


def test_second_login_reuses_person_and_updates_username(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _gh = wired
    # First login.
    state1, _ = _login_and_get_state(client)
    client.get(f"/api/auth/github/callback?code=a&state={state1}", follow_redirects=False)
    first_person_count = len(session.scalars(select(Person)).all())

    # Clear cookies to simulate a fresh browser, then log in again.
    client.cookies.clear()
    state2, _ = _login_and_get_state(client)
    client.get(f"/api/auth/github/callback?code=b&state={state2}", follow_redirects=False)

    assert len(session.scalars(select(Person)).all()) == first_person_count
    assert len(session.scalars(select(ExternalIdentity)).all()) == 1


def test_state_replay_is_rejected(wired) -> None:  # type: ignore[no-untyped-def]
    client, _session, _gh = wired
    state, _ = _login_and_get_state(client)
    first = client.get(f"/api/auth/github/callback?code=a&state={state}", follow_redirects=False)
    assert first.status_code == 302

    # Replaying the same (now consumed) state must fail.
    replay = client.get(f"/api/auth/github/callback?code=a&state={state}", follow_redirects=False)
    assert replay.status_code == 400


def test_mismatched_state_is_rejected(wired) -> None:  # type: ignore[no-untyped-def]
    client, _session, _gh = wired
    _login_and_get_state(client)
    resp = client.get(
        "/api/auth/github/callback?code=a&state=not-the-real-state",
        follow_redirects=False,
    )
    assert resp.status_code == 400


def test_callback_without_binding_cookie_is_rejected(wired) -> None:  # type: ignore[no-untyped-def]
    client, _session, _gh = wired
    state, _ = _login_and_get_state(client)
    # Drop the browser-binding cookie: the callback is not from the initiating
    # browser and must be rejected.
    client.cookies.delete(OAUTH_BINDING_COOKIE)
    resp = client.get(f"/api/auth/github/callback?code=a&state={state}", follow_redirects=False)
    assert resp.status_code == 400


def test_logout_invalidates_session(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _gh = wired
    state, _ = _login_and_get_state(client)
    client.get(f"/api/auth/github/callback?code=a&state={state}", follow_redirects=False)
    csrf = client.cookies.get("community_csrf")

    resp = client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf or ""})
    assert resp.status_code == 204
    assert session.scalars(select(UserSession)).all() == []

    # Subsequent access is anonymous.
    assert client.get("/api/me").status_code == 401


def test_logout_without_csrf_is_forbidden(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _gh = wired
    state, _ = _login_and_get_state(client)
    client.get(f"/api/auth/github/callback?code=a&state={state}", follow_redirects=False)

    # No CSRF header -> 403; session remains valid.
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 403
    assert len(session.scalars(select(UserSession)).all()) == 1


def test_consumed_state_row_is_deleted(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _gh = wired
    state, _ = _login_and_get_state(client)
    assert len(session.scalars(select(OAuthState)).all()) == 1
    client.get(f"/api/auth/github/callback?code=a&state={state}", follow_redirects=False)
    assert session.scalars(select(OAuthState)).all() == []
