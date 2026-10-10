"""Program domain model.

A Program is a reusable category of contributor activity — GSoC, an internship,
a university residency, a volunteer initiative, etc. (product-design.md §3). A
Program owns one or more Editions.

The domain does not hardcode GSoC: ``kind`` is a small controlled vocabulary
stored as VARCHAR + CHECK (matching the ExternalIdentity provider idiom), so
adding a kind is a plain data change rather than a native-enum migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Final

from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.edition import Edition

PROGRAM_KIND_GSOC: Final = "gsoc"
PROGRAM_KIND_INTERNSHIP: Final = "internship"
PROGRAM_KIND_RESIDENCY: Final = "residency"
PROGRAM_KIND_VOLUNTEER: Final = "volunteer"
PROGRAM_KIND_OTHER: Final = "other"
PROGRAM_KINDS: Final = (
    PROGRAM_KIND_GSOC,
    PROGRAM_KIND_INTERNSHIP,
    PROGRAM_KIND_RESIDENCY,
    PROGRAM_KIND_VOLUNTEER,
    PROGRAM_KIND_OTHER,
)

_KINDS_SQL: Final = ", ".join(f"'{k}'" for k in PROGRAM_KINDS)


class Program(Base):
    """A reusable category of contributor activity."""

    __tablename__ = "programs"

    __table_args__ = (
        CheckConstraint(f"kind IN ({_KINDS_SQL})", name="kind_valid"),
        UniqueConstraint("slug", name="uq_programs_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Stable, URL-friendly identifier, unique across programs (e.g. "gsoc").
    slug: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32))
    description: Mapped[str | None] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # NOTE: `onupdate` is applied by SQLAlchemy on ORM flush, NOT a database
    # trigger. Writes that bypass the ORM will not update this column.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    editions: Mapped[list[Edition]] = relationship(back_populates="program")
