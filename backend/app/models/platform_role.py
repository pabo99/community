"""Platform-level authorization roles.

A ``PlatformRole`` grants a Person a platform-wide role. The only role at
M1-07 is ``superadmin``; the model is a table (not a boolean on Person) so
roles are explicit, auditable, and extensible without a schema change per role.

Project-scoped roles (mentor assignments) are a separate, later concern
(M1-07b) and are not modeled here.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Final

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ROLE_SUPERADMIN: Final = "superadmin"
PLATFORM_ROLES: Final = (ROLE_SUPERADMIN,)

_ROLES_SQL: Final = ", ".join(f"'{r}'" for r in PLATFORM_ROLES)


class PlatformRole(Base):
    """A platform-wide role granted to a Person."""

    __tablename__ = "platform_roles"

    __table_args__ = (
        CheckConstraint(f"role IN ({_ROLES_SQL})", name="role_valid"),
        # At most one row per (person, role): makes grants idempotent at the
        # database level and prevents duplicate role rows under concurrency.
        UniqueConstraint("person_id", "role", name="uq_platform_roles_person_id_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
