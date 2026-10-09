"""Integration tests for the superadmin bootstrap command."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.cli.bootstrap_admins import bootstrap_admins
from app.models.external_identity import PROVIDER_GITHUB, ExternalIdentity
from app.models.person import Person
from app.models.platform_role import ROLE_SUPERADMIN, PlatformRole
from sqlalchemy import Engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


@pytest.fixture
def db_session(migrated_engine: Engine) -> Iterator[Session]:
    """Savepoint-isolated session: the command's commit() only releases a
    savepoint, and the outer transaction is rolled back after the test."""
    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


def _make_github_person(session: Session, github_id: str, login: str) -> Person:
    person = Person(display_name=login)
    session.add(person)
    session.flush()
    session.add(
        ExternalIdentity(
            person=person,
            provider=PROVIDER_GITHUB,
            provider_user_id=github_id,
            username=login,
        )
    )
    session.flush()
    return person


def _count_roles(session: Session, person_id, role: str) -> int:  # type: ignore[no-untyped-def]
    return len(
        session.scalars(
            select(PlatformRole).where(
                PlatformRole.person_id == person_id, PlatformRole.role == role
            )
        ).all()
    )


def test_bootstrap_grants_superadmin_by_github_id(db_session: Session) -> None:
    person = _make_github_person(db_session, "12345", "pabo99")

    granted = bootstrap_admins(db_session, ["12345"], log=lambda _m: None)

    assert granted == 1
    assert _count_roles(db_session, person.id, ROLE_SUPERADMIN) == 1


def test_bootstrap_is_idempotent_on_rerun(db_session: Session) -> None:
    person = _make_github_person(db_session, "12345", "pabo99")

    first = bootstrap_admins(db_session, ["12345"], log=lambda _m: None)
    second = bootstrap_admins(db_session, ["12345"], log=lambda _m: None)

    assert first == 1
    assert second == 0  # no new grant on rerun
    assert _count_roles(db_session, person.id, ROLE_SUPERADMIN) == 1


def test_bootstrap_skips_github_id_without_identity(db_session: Session) -> None:
    # No identity exists for this id: it is skipped, nothing is created.
    granted = bootstrap_admins(db_session, ["99999"], log=lambda _m: None)
    assert granted == 0
    assert db_session.scalars(select(PlatformRole)).all() == []
    assert db_session.scalars(select(Person)).all() == []


def test_bootstrap_empty_config_is_noop(db_session: Session) -> None:
    assert bootstrap_admins(db_session, [], log=lambda _m: None) == 0


def test_bootstrap_does_not_touch_unrelated_persons(db_session: Session) -> None:
    target = _make_github_person(db_session, "100", "target")
    other = _make_github_person(db_session, "200", "other")

    bootstrap_admins(db_session, ["100"], log=lambda _m: None)

    assert _count_roles(db_session, target.id, ROLE_SUPERADMIN) == 1
    assert _count_roles(db_session, other.id, ROLE_SUPERADMIN) == 0


def test_bootstrap_grants_multiple_configured_ids(db_session: Session) -> None:
    a = _make_github_person(db_session, "100", "a")
    b = _make_github_person(db_session, "200", "b")

    granted = bootstrap_admins(db_session, ["100", "200"], log=lambda _m: None)

    assert granted == 2
    assert _count_roles(db_session, a.id, ROLE_SUPERADMIN) == 1
    assert _count_roles(db_session, b.id, ROLE_SUPERADMIN) == 1


def test_duplicate_role_grant_is_rejected_by_db(db_session: Session) -> None:
    # The invariant the bootstrap's idempotency relies on: the DB enforces at
    # most one (person_id, role) row.
    person = _make_github_person(db_session, "100", "a")
    db_session.add(PlatformRole(person_id=person.id, role=ROLE_SUPERADMIN))
    db_session.flush()

    db_session.add(PlatformRole(person_id=person.id, role=ROLE_SUPERADMIN))
    with pytest.raises(IntegrityError):
        db_session.flush()
