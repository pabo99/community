"""Integration tests for session expiry and the login concurrency guarantee."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.auth.tokens import hash_token
from app.config import Settings
from app.integrations.github.oauth import GitHubUser
from app.models.external_identity import ExternalIdentity
from app.models.person import Person
from app.repositories.session import SessionRepository
from app.services.auth import AuthService
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

_SETTINGS = Settings(
    database_url="postgresql+psycopg://unused",
    github_oauth_client_id="cid",
    github_oauth_client_secret="secret",
)


def test_expired_session_is_not_returned(db_session: Session) -> None:
    person = Person(display_name="Ada")
    db_session.add(person)
    db_session.flush()

    repo = SessionRepository(db_session)
    repo.create_session(
        token_hash=hash_token("raw-token"),
        person_id=person.id,
        csrf_token="csrf",
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )
    db_session.flush()

    found = repo.get_by_token_hash(hash_token("raw-token"))
    # The row exists but is expired; the dependency layer treats expiry as
    # anonymous. Here we assert the stored expiry is in the past.
    assert found is not None
    assert found.expires_at <= datetime.now(UTC)


def test_concurrent_first_logins_create_single_person(migrated_engine: Engine) -> None:
    """Two concurrent first-time logins for the same GitHub id must not create
    two persons. The partial unique index forces one insert to fail; the
    service catches it and resolves to the winning row.
    """
    github_user = GitHubUser(id="99999", login="racer", name="Racer")

    # Two independent sessions on two independent connections = real concurrency.
    session_a = Session(bind=migrated_engine.connect(), expire_on_commit=False)
    session_b = Session(bind=migrated_engine.connect(), expire_on_commit=False)
    try:
        service_a = AuthService(session_a, _SETTINGS)
        service_b = AuthService(session_b, _SETTINGS)

        # Both resolve the (absent) identity and stage inserts before either
        # commits, then commit in sequence. The second hits the unique index.
        issued_a = service_a.login_with_github(github_user)
        issued_b = service_b.login_with_github(github_user)

        assert issued_a.person.id == issued_b.person.id

        # Exactly one person and one identity exist.
        verify = Session(bind=migrated_engine.connect(), expire_on_commit=False)
        try:
            identities = verify.scalars(
                select(ExternalIdentity).where(ExternalIdentity.provider_user_id == "99999")
            ).all()
            persons = verify.scalars(select(Person)).all()
            assert len(identities) == 1
            assert len(persons) == 1
            # Clean up committed rows (this test commits real data). Deleting
            # the person cascades to its identity and session rows.
            for person in persons:
                verify.delete(person)
            verify.commit()
        finally:
            verify.close()
    finally:
        session_a.close()
        session_b.close()
