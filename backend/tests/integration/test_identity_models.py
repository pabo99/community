"""Integration tests for the identity schema against real PostgreSQL.

Covers constraint enforcement at the database level: duplicate stable ids,
nullable identifiers, the GitHub stable-id requirement, username reuse,
multiple identities per person, foreign-key cascade, and transaction rollback.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.models.external_identity import (
    PROVIDER_DISCORD,
    PROVIDER_GITHUB,
    PROVIDER_OMEGAUP,
    ExternalIdentity,
)
from app.models.person import Person
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def _make_person(session: Session, display_name: str | None = None) -> Person:
    person = Person(display_name=display_name)
    session.add(person)
    session.flush()
    return person


def test_create_person_with_github_identity(db_session: Session) -> None:
    person = _make_person(db_session, display_name="Ada")
    identity = ExternalIdentity(
        person=person,
        provider=PROVIDER_GITHUB,
        provider_user_id="12345",
        username="ada",
        verified_at=datetime.now(UTC),
    )
    db_session.add(identity)
    db_session.flush()
    db_session.expire_all()

    reloaded = db_session.get(Person, person.id)
    assert reloaded is not None
    assert reloaded.id is not None
    assert reloaded.created_at is not None
    assert len(reloaded.identities) == 1
    assert reloaded.identities[0].provider == PROVIDER_GITHUB
    assert reloaded.identities[0].provider_user_id == "12345"
    assert reloaded.identities[0].verified_at is not None


def test_person_can_have_multiple_identities(db_session: Session) -> None:
    person = _make_person(db_session)
    db_session.add_all(
        [
            ExternalIdentity(person=person, provider=PROVIDER_GITHUB, provider_user_id="1"),
            ExternalIdentity(person=person, provider=PROVIDER_OMEGAUP, username="ada_ou"),
            ExternalIdentity(person=person, provider=PROVIDER_DISCORD, username="ada#1"),
        ]
    )
    db_session.flush()
    db_session.expire_all()

    providers = {i.provider for i in db_session.get(Person, person.id).identities}  # type: ignore[union-attr]
    assert providers == {PROVIDER_GITHUB, PROVIDER_OMEGAUP, PROVIDER_DISCORD}


def test_duplicate_stable_id_rejected(db_session: Session) -> None:
    person = _make_person(db_session)
    db_session.add(
        ExternalIdentity(person=person, provider=PROVIDER_GITHUB, provider_user_id="999")
    )
    db_session.flush()

    db_session.add(
        ExternalIdentity(person=person, provider=PROVIDER_GITHUB, provider_user_id="999")
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_stable_id_different_provider_allowed(db_session: Session) -> None:
    # The unique index is scoped to (provider, provider_user_id), so the same
    # raw id under a different provider does not collide.
    person = _make_person(db_session)
    db_session.add_all(
        [
            ExternalIdentity(person=person, provider=PROVIDER_GITHUB, provider_user_id="42"),
            ExternalIdentity(person=person, provider=PROVIDER_OMEGAUP, provider_user_id="42"),
        ]
    )
    db_session.flush()  # must not raise


def test_null_stable_ids_do_not_collide(db_session: Session) -> None:
    # Partial unique index excludes NULL provider_user_id, so multiple
    # identities with a NULL stable id for the same provider are allowed.
    person = _make_person(db_session)
    db_session.add_all(
        [
            ExternalIdentity(person=person, provider=PROVIDER_DISCORD, username="a"),
            ExternalIdentity(person=person, provider=PROVIDER_DISCORD, username="b"),
        ]
    )
    db_session.flush()  # must not raise


def test_github_requires_non_empty_stable_id(db_session: Session) -> None:
    person = _make_person(db_session)
    db_session.add(ExternalIdentity(person=person, provider=PROVIDER_GITHUB, provider_user_id=None))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_github_rejects_empty_string_stable_id(db_session: Session) -> None:
    person = _make_person(db_session)
    db_session.add(ExternalIdentity(person=person, provider=PROVIDER_GITHUB, provider_user_id=""))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_non_github_provider_allows_null_stable_id(db_session: Session) -> None:
    person = _make_person(db_session)
    db_session.add(
        ExternalIdentity(person=person, provider=PROVIDER_OMEGAUP, username="only-username")
    )
    db_session.flush()  # must not raise


def test_invalid_provider_rejected(db_session: Session) -> None:
    person = _make_person(db_session)
    db_session.add(ExternalIdentity(person=person, provider="gitlab", provider_user_id="1"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_username_reuse_is_allowed(db_session: Session) -> None:
    # Usernames are mutable and may be reassigned; (provider, username) is NOT
    # unique. Two distinct GitHub accounts may carry the same login over time.
    person = _make_person(db_session)
    db_session.add_all(
        [
            ExternalIdentity(
                person=person, provider=PROVIDER_GITHUB, provider_user_id="100", username="ghost"
            ),
            ExternalIdentity(
                person=person, provider=PROVIDER_GITHUB, provider_user_id="200", username="ghost"
            ),
        ]
    )
    db_session.flush()  # must not raise


def test_foreign_key_cascade_deletes_identities(db_session: Session) -> None:
    person = _make_person(db_session)
    db_session.add(ExternalIdentity(person=person, provider=PROVIDER_GITHUB, provider_user_id="7"))
    db_session.flush()
    person_id = person.id

    # DB-level cascade: delete the person row directly and confirm identities go.
    db_session.execute(text("DELETE FROM persons WHERE id = :pid"), {"pid": person_id})
    db_session.flush()

    remaining = db_session.scalars(
        select(ExternalIdentity).where(ExternalIdentity.person_id == person_id)
    ).all()
    assert remaining == []


def test_rollback_leaves_no_partial_state(db_session: Session) -> None:
    person = _make_person(db_session)
    db_session.add(
        ExternalIdentity(person=person, provider=PROVIDER_GITHUB, provider_user_id="321")
    )
    db_session.flush()

    # Trigger a constraint violation, then roll back to a clean savepoint.
    savepoint = db_session.begin_nested()
    db_session.add(
        ExternalIdentity(person=person, provider=PROVIDER_GITHUB, provider_user_id="321")
    )
    with pytest.raises(IntegrityError):
        db_session.flush()
    savepoint.rollback()

    # The original identity survives; the duplicate was never persisted.
    identities = db_session.scalars(
        select(ExternalIdentity).where(ExternalIdentity.provider_user_id == "321")
    ).all()
    assert len(identities) == 1
