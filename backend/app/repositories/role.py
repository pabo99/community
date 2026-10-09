"""Persistence for platform roles.

Methods never commit; the caller owns the transaction boundary. ``grant_role``
is idempotent at the database level via the ``(person_id, role)`` unique
constraint.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.platform_role import ROLE_SUPERADMIN, PlatformRole


class RoleRepository:
    """Data access for PlatformRole."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_role(self, person_id: uuid.UUID, role: str) -> PlatformRole | None:
        stmt = select(PlatformRole).where(
            PlatformRole.person_id == person_id,
            PlatformRole.role == role,
        )
        return self._session.scalars(stmt).one_or_none()

    def list_roles(self, person_id: uuid.UUID) -> list[str]:
        stmt = select(PlatformRole.role).where(PlatformRole.person_id == person_id)
        return list(self._session.scalars(stmt).all())

    def has_role(self, person_id: uuid.UUID, role: str) -> bool:
        return self.get_role(person_id, role) is not None

    def is_superadmin(self, person_id: uuid.UUID) -> bool:
        return self.has_role(person_id, ROLE_SUPERADMIN)

    def grant_role(self, person_id: uuid.UUID, role: str) -> PlatformRole:
        """Stage a role grant if absent (idempotent). Returns the row.

        The caller should flush within a SAVEPOINT if it needs to tolerate a
        concurrent grant hitting the unique constraint.
        """
        existing = self.get_role(person_id, role)
        if existing is not None:
            return existing
        platform_role = PlatformRole(person_id=person_id, role=role)
        self._session.add(platform_role)
        return platform_role
