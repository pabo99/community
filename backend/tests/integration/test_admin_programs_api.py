"""Integration tests for the admin Program/Edition REST API (M1-09).

Real PostgreSQL via the shared build_client harness. Covers authorization,
CSRF, CRUD happy paths, validation (422), conflicts (409), not-found (404),
persistence, immutable-field rejection, and the OpenAPI contract.
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

_GH_USER = GitHubUser(id="4242", login="admin", name="Admin")


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


def _grant_superadmin(client: TestClient, session: Session) -> None:
    identity = session.scalars(
        select(ExternalIdentity).where(ExternalIdentity.provider_user_id == _GH_USER.id)
    ).one()
    RoleRepository(session).grant_role(identity.person_id, ROLE_SUPERADMIN)
    session.flush()


def _csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.cookies.get("community_csrf") or ""}


def _admin(client: TestClient, session: Session) -> None:
    _login(client)
    _grant_superadmin(client, session)


# --- Authorization & CSRF ----------------------------------------------------


def test_list_programs_401_anonymous(wired) -> None:  # type: ignore[no-untyped-def]
    client, _s, _g = wired
    assert client.get("/api/admin/programs").status_code == 401


def test_list_programs_403_non_admin(wired) -> None:  # type: ignore[no-untyped-def]
    client, _s, _g = wired
    _login(client)
    assert client.get("/api/admin/programs").status_code == 403


def test_create_program_403_non_admin(wired) -> None:  # type: ignore[no-untyped-def]
    client, _s, _g = wired
    _login(client)
    resp = client.post(
        "/api/admin/programs",
        json={"slug": "gsoc", "name": "GSoC", "kind": "gsoc"},
        headers=_csrf(client),
    )
    assert resp.status_code == 403


def test_create_program_403_without_csrf(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    resp = client.post(
        "/api/admin/programs",
        json={"slug": "gsoc", "name": "GSoC", "kind": "gsoc"},
    )
    assert resp.status_code == 403


# --- Program CRUD ------------------------------------------------------------


def test_program_create_read_list_update(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)

    created = client.post(
        "/api/admin/programs",
        json={"slug": "gsoc", "name": "GSoC", "kind": "gsoc", "description": "Summer"},
        headers=_csrf(client),
    )
    assert created.status_code == 201
    body = created.json()
    program_id = body["id"]
    assert body["slug"] == "gsoc"
    assert body["kind"] == "gsoc"

    assert any(p["id"] == program_id for p in client.get("/api/admin/programs").json())

    read = client.get(f"/api/admin/programs/{program_id}")
    assert read.status_code == 200
    assert read.json()["name"] == "GSoC"

    patched = client.patch(
        f"/api/admin/programs/{program_id}",
        json={"name": "Google Summer of Code", "description": None},
        headers=_csrf(client),
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Google Summer of Code"
    assert patched.json()["description"] is None


def test_program_duplicate_slug_conflict(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    payload = {"slug": "gsoc", "name": "GSoC", "kind": "gsoc"}
    first = client.post("/api/admin/programs", json=payload, headers=_csrf(client))
    assert first.status_code == 201
    dup = client.post("/api/admin/programs", json=payload, headers=_csrf(client))
    assert dup.status_code == 409
    # No raw PostgreSQL error leaks.
    assert "psycopg" not in dup.text and "IntegrityError" not in dup.text


def test_program_invalid_kind_422(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    resp = client.post(
        "/api/admin/programs",
        json={"slug": "x", "name": "X", "kind": "bootcamp"},
        headers=_csrf(client),
    )
    assert resp.status_code == 422


def test_program_invalid_slug_pattern_422(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    resp = client.post(
        "/api/admin/programs",
        json={"slug": "Not A Slug", "name": "X", "kind": "other"},
        headers=_csrf(client),
    )
    assert resp.status_code == 422


def test_program_update_rejects_immutable_slug(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    created = client.post(
        "/api/admin/programs",
        json={"slug": "gsoc", "name": "GSoC", "kind": "gsoc"},
        headers=_csrf(client),
    )
    program_id = created.json()["id"]
    # Attempting to change the immutable slug is rejected (extra=forbid), not ignored.
    resp = client.patch(
        f"/api/admin/programs/{program_id}",
        json={"slug": "gsoc-renamed"},
        headers=_csrf(client),
    )
    assert resp.status_code == 422


def test_program_read_404(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    resp = client.get("/api/admin/programs/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# --- Edition CRUD ------------------------------------------------------------


def _create_program(client: TestClient) -> str:
    resp = client.post(
        "/api/admin/programs",
        json={"slug": "gsoc", "name": "GSoC", "kind": "gsoc"},
        headers=_csrf(client),
    )
    program_id: str = resp.json()["id"]
    return program_id


def test_edition_create_read_list_update(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    program_id = _create_program(client)

    created = client.post(
        f"/api/admin/programs/{program_id}/editions",
        json={
            "slug": "2027",
            "name": "GSoC 2027",
            "status": "open",
            "starts_on": "2027-05-01",
            "ends_on": "2027-08-01",
        },
        headers=_csrf(client),
    )
    assert created.status_code == 201
    edition = created.json()
    edition_id = edition["id"]
    assert edition["status"] == "open"
    assert edition["source"] == "community"
    assert edition["external_id"] is None

    listed = client.get(f"/api/admin/programs/{program_id}/editions")
    assert [e["id"] for e in listed.json()] == [edition_id]

    read = client.get(f"/api/admin/editions/{edition_id}")
    assert read.status_code == 200

    patched = client.patch(
        f"/api/admin/editions/{edition_id}",
        json={"status": "in_progress", "ends_on": None},
        headers=_csrf(client),
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "in_progress"
    assert patched.json()["ends_on"] is None


def test_edition_default_status_is_draft(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    program_id = _create_program(client)
    created = client.post(
        f"/api/admin/programs/{program_id}/editions",
        json={"slug": "2027", "name": "GSoC 2027"},
        headers=_csrf(client),
    )
    assert created.status_code == 201
    assert created.json()["status"] == "draft"


def test_edition_duplicate_slug_in_program_conflict(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    program_id = _create_program(client)
    payload = {"slug": "2027", "name": "GSoC 2027"}
    client.post(f"/api/admin/programs/{program_id}/editions", json=payload, headers=_csrf(client))
    dup = client.post(
        f"/api/admin/programs/{program_id}/editions", json=payload, headers=_csrf(client)
    )
    assert dup.status_code == 409
    assert "psycopg" not in dup.text


def test_edition_bad_date_range_422_on_create(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    program_id = _create_program(client)
    resp = client.post(
        f"/api/admin/programs/{program_id}/editions",
        json={"slug": "2027", "name": "E", "starts_on": "2027-08-01", "ends_on": "2027-05-01"},
        headers=_csrf(client),
    )
    assert resp.status_code == 422


def test_edition_combined_date_range_422_on_patch(wired) -> None:  # type: ignore[no-untyped-def]
    # starts_on stored; PATCH sets only ends_on earlier -> combined range invalid.
    client, session, _g = wired
    _admin(client, session)
    program_id = _create_program(client)
    created = client.post(
        f"/api/admin/programs/{program_id}/editions",
        json={"slug": "2027", "name": "E", "starts_on": "2027-06-01"},
        headers=_csrf(client),
    )
    edition_id = created.json()["id"]
    resp = client.patch(
        f"/api/admin/editions/{edition_id}",
        json={"ends_on": "2027-05-01"},
        headers=_csrf(client),
    )
    assert resp.status_code == 422


def test_edition_community_with_external_id_422(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    program_id = _create_program(client)
    resp = client.post(
        f"/api/admin/programs/{program_id}/editions",
        json={"slug": "2027", "name": "E", "source": "community", "external_id": "x"},
        headers=_csrf(client),
    )
    assert resp.status_code == 422


def test_edition_omegaup_requires_external_id_422(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    program_id = _create_program(client)
    resp = client.post(
        f"/api/admin/programs/{program_id}/editions",
        json={"slug": "2027", "name": "E", "source": "omegaup"},
        headers=_csrf(client),
    )
    assert resp.status_code == 422


def test_edition_omegaup_with_external_id_created(wired) -> None:  # type: ignore[no-untyped-def]
    # Manually-entered omegaUp provenance is accepted as a reference; no sync.
    client, session, _g = wired
    _admin(client, session)
    program_id = _create_program(client)
    resp = client.post(
        f"/api/admin/programs/{program_id}/editions",
        json={"slug": "2027", "name": "E", "source": "omegaup", "external_id": "omg-9"},
        headers=_csrf(client),
    )
    assert resp.status_code == 201
    assert resp.json()["source"] == "omegaup"
    assert resp.json()["external_id"] == "omg-9"


def test_edition_update_rejects_immutable_source(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    program_id = _create_program(client)
    created = client.post(
        f"/api/admin/programs/{program_id}/editions",
        json={"slug": "2027", "name": "E"},
        headers=_csrf(client),
    )
    edition_id = created.json()["id"]
    for field in ({"source": "omegaup"}, {"external_id": "x"}, {"slug": "2028"}):
        resp = client.patch(f"/api/admin/editions/{edition_id}", json=field, headers=_csrf(client))
        assert resp.status_code == 422, field


def test_create_edition_under_unknown_program_404(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    resp = client.post(
        "/api/admin/programs/00000000-0000-0000-0000-000000000000/editions",
        json={"slug": "2027", "name": "E"},
        headers=_csrf(client),
    )
    assert resp.status_code == 404


def test_edition_read_404(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    resp = client.get("/api/admin/editions/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# --- Persistence -------------------------------------------------------------


def test_program_persists_across_requests(wired) -> None:  # type: ignore[no-untyped-def]
    client, session, _g = wired
    _admin(client, session)
    created = client.post(
        "/api/admin/programs",
        json={"slug": "internship", "name": "Internship", "kind": "internship"},
        headers=_csrf(client),
    )
    program_id = created.json()["id"]
    # Fresh read reflects persisted state.
    again = client.get(f"/api/admin/programs/{program_id}")
    assert again.json()["slug"] == "internship"


# --- OpenAPI contract --------------------------------------------------------


def test_openapi_exposes_admin_program_edition_paths(wired) -> None:  # type: ignore[no-untyped-def]
    client, _s, _g = wired
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    assert "/api/admin/programs" in paths
    assert "/api/admin/programs/{program_id}" in paths
    assert "/api/admin/programs/{program_id}/editions" in paths
    assert "/api/admin/editions/{edition_id}" in paths
    assert "get" in paths["/api/admin/programs"]
    assert "post" in paths["/api/admin/programs"]
    assert "patch" in paths["/api/admin/programs/{program_id}"]
    # Response schemas are registered.
    assert "ProgramResponse" in spec["components"]["schemas"]
    assert "EditionResponse" in spec["components"]["schemas"]
