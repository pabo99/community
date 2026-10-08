"""Integration tests for IdentityRepository against real PostgreSQL."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.models.external_identity import PROVIDER_DISCORD, PROVIDER_GITHUB, PROVIDER_OMEGAUP
from app.repositories.identity import IdentityRepository
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def test_create_person_and_add_identity(db_session: Session) -> None:
    repo = IdentityRepository(db_session)
    person = repo.create_person(display_name="Grace")
    repo.add_identity(
        person=person,
        provider=PROVIDER_GITHUB,
        provider_user_id="555",
        username="grace",
        verified_at=datetime.now(UTC),
    )
    repo.flush()

    assert person.id is not None
    found = repo.get_by_provider_identifier(PROVIDER_GITHUB, "555")
    assert found is not None
    assert found.person_id == person.id
    assert found.username == "grace"


def test_get_by_provider_identifier_uses_stable_id_not_username(db_session: Session) -> None:
    repo = IdentityRepository(db_session)
    person = repo.create_person()
    repo.add_identity(
        person=person, provider=PROVIDER_GITHUB, provider_user_id="1001", username="renamed"
    )
    repo.flush()

    # Canonical lookup is by stable id.
    assert repo.get_by_provider_identifier(PROVIDER_GITHUB, "1001") is not None
    # A different provider with the same raw id does not match.
    assert repo.get_by_provider_identifier(PROVIDER_OMEGAUP, "1001") is None


def test_get_by_provider_identifier_returns_none_when_absent(db_session: Session) -> None:
    repo = IdentityRepository(db_session)
    assert repo.get_by_provider_identifier(PROVIDER_GITHUB, "does-not-exist") is None


def test_list_identities_for_person(db_session: Session) -> None:
    repo = IdentityRepository(db_session)
    person = repo.create_person()
    repo.add_identity(person=person, provider=PROVIDER_GITHUB, provider_user_id="2001")
    repo.add_identity(person=person, provider=PROVIDER_DISCORD, username="g#1")
    repo.flush()

    identities = repo.list_identities_for_person(person.id)
    assert {i.provider for i in identities} == {PROVIDER_GITHUB, PROVIDER_DISCORD}


def test_get_person_roundtrip(db_session: Session) -> None:
    repo = IdentityRepository(db_session)
    person = repo.create_person(display_name="Alan")
    repo.flush()

    assert repo.get_person(person.id) is person
    assert repo.get_person(uuid.uuid4()) is None


def test_repository_does_not_commit(db_session: Session) -> None:
    # The repository only flushes; the surrounding transaction (rolled back by
    # the db_session fixture) still owns the commit decision.
    repo = IdentityRepository(db_session)
    person = repo.create_person()
    repo.add_identity(person=person, provider=PROVIDER_GITHUB, provider_user_id="3001")
    repo.flush()

    # Still inside an open transaction (no commit happened in the repository).
    assert db_session.in_transaction()


def test_duplicate_stable_id_via_repository_raises(db_session: Session) -> None:
    repo = IdentityRepository(db_session)
    person = repo.create_person()
    repo.add_identity(person=person, provider=PROVIDER_GITHUB, provider_user_id="4001")
    repo.flush()

    repo.add_identity(person=person, provider=PROVIDER_GITHUB, provider_user_id="4001")
    with pytest.raises(IntegrityError):
        repo.flush()
