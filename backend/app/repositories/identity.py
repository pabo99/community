"""Identity persistence: Person and ExternalIdentity.

This repository provides explicit, composable primitives for creating and
retrieving persons and identities. It deliberately does NOT implement a
race-prone "find-or-create": the concurrent OAuth login flow (lookup, insert,
unique-violation handling) is owned by M1-06, which can coordinate it against
the unique constraints enforced here.

Lookups use the stable provider identifier (``provider_user_id``) as the
canonical key, never the mutable username.

Methods never commit. The caller (a service/use-case or a test) owns the
transaction boundary. ``flush`` is offered so callers can surface integrity
errors within their own transaction without committing.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.external_identity import ExternalIdentity
from app.models.person import Person


class IdentityRepository:
    """Data access for Person and ExternalIdentity."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Person --------------------------------------------------------------

    def create_person(self, *, display_name: str | None = None) -> Person:
        """Create and stage a new Person (not committed)."""
        person = Person(display_name=display_name)
        self._session.add(person)
        return person

    def get_person(self, person_id: uuid.UUID) -> Person | None:
        return self._session.get(Person, person_id)

    # --- ExternalIdentity ----------------------------------------------------

    def add_identity(
        self,
        *,
        person: Person,
        provider: str,
        provider_user_id: str | None = None,
        username: str | None = None,
        verified_at: datetime | None = None,
    ) -> ExternalIdentity:
        """Create and stage a new identity for ``person`` (not committed)."""
        identity = ExternalIdentity(
            person=person,
            provider=provider,
            provider_user_id=provider_user_id,
            username=username,
            verified_at=verified_at,
        )
        self._session.add(identity)
        return identity

    def get_identity(self, identity_id: uuid.UUID) -> ExternalIdentity | None:
        return self._session.get(ExternalIdentity, identity_id)

    def get_by_provider_identifier(
        self, provider: str, provider_user_id: str
    ) -> ExternalIdentity | None:
        """Return the identity for a provider's stable id, or ``None``.

        This is the canonical lookup used by authentication flows.
        """
        stmt = select(ExternalIdentity).where(
            ExternalIdentity.provider == provider,
            ExternalIdentity.provider_user_id == provider_user_id,
        )
        return self._session.scalars(stmt).one_or_none()

    def list_identities_for_person(self, person_id: uuid.UUID) -> list[ExternalIdentity]:
        stmt = select(ExternalIdentity).where(ExternalIdentity.person_id == person_id)
        return list(self._session.scalars(stmt).all())

    # --- Transaction helpers -------------------------------------------------

    def flush(self) -> None:
        """Flush staged changes to surface integrity errors (no commit)."""
        self._session.flush()
