"""Person domain model.

A Person is the identity anchor for a contributor, mentor, or administrator
(product-design.md §3). A Person may have multiple external identities
(GitHub, omegaUp, Discord). Roles, program participation, and profile data are
intentionally out of scope here and arrive in later milestone issues.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.external_identity import ExternalIdentity


class Person(Base):
    """A person known to the platform."""

    __tablename__ = "persons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    display_name: Mapped[str | None] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    # NOTE: `onupdate` is applied by SQLAlchemy on ORM flush, NOT a database
    # trigger. Writes that bypass the ORM will not update this column.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    identities: Mapped[list[ExternalIdentity]] = relationship(
        back_populates="person",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
