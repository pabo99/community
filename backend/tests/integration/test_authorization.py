"""Integration tests for the authorization foundation (M1-07).

Verifies 401 (anonymous), 403 (authenticated non-admin), and 200 (superadmin)
on a protected admin endpoint, plus the /api/me role flag.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.config import Settings
from app.integrations.github.oauth import GitHubUser
from app.models.external_identity import ExternalIdentity
from app.models.platform_role import ROLE_SUPERADMIN
from app.repositories.role import RoleRepository
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from tests.integration.conftest_auth import build_client, make_auth_settings

pytestmark = pytest.mark.integration

_GH_USER = GitHubUser(id="777", login="admin-user", name="Admin User")


@pytest.fixture
def auth_settings() -> Settings:
    return make_auth_settings()


@pytest.fixture
def wired(
    migrated_engine: Engine, auth_settings: Settings
) -> Iterator[tuple[TestClient, Session, object]]:
    yield from build_client(migrated_engine, auth_settings, _GH_USER)


def _login(client: TestClient) -> None:
    resp = client.get("/api/auth/github/login", follow_redirects=False)
    state = resp.headers["location"].split("state=")[1]
    client.get(f"/api/auth/github/callback?code=c&state={state}", follow_redirects=False)


def _make_current_superadmin(client: TestClient, session: Session) -> None:
    identity = session.scalars(
        select(ExternalIdentity).where(ExternalIdentity.provider_user_id == _GH_USER.id)
    ).one()
    RoleRepository(session).grant_role(identity.person_id, ROLE_SUPERADMIN)
    session.flush()


def test_admin_endpoint_401_when_anonymous(wired) -> None:  # type: ignore[no-untyped-def]
    client, _session, _gh = wired
    assert client.get("/api/admin/ping").status_code == 401


def test_admin_endpoint_403_when_authenticated_non_admin(wired) -> None:  # type: ignore[no-untyped-def]
    client, _session, _gh = wired
    _login(client)
    assert client.get("/api/admin/ping").status_code == 403


def test_admin_endpoint_200_when_superadmin(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _gh = wired
    _login(client)
    _make_current_superadmin(client, session)

    resp = client.get("/api/admin/ping")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_me_reports_superadmin_false_for_regular_user(wired) -> None:  # type: ignore[no-untyped-def]
    client, _session, _gh = wired
    _login(client)
    resp = client.get("/api/me")
    assert resp.status_code == 200
    assert resp.json()["is_superadmin"] is False


def test_me_reports_superadmin_true_after_grant(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _gh = wired
    _login(client)
    _make_current_superadmin(client, session)
    resp = client.get("/api/me")
    assert resp.status_code == 200
    assert resp.json()["is_superadmin"] is True
