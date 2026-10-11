"""Program domain model.

A Program is a reusable contributor-program catalog entry — GSoC, Professional
Internships, Professional Residencies, Volunteering, or an exceptional
admin-created program (product-design.md §3, §20.2). A Program owns one or more
Editions.

The program catalog itself is the set of program categories, so there is no
separate ``kind`` enum (it would duplicate the catalog). Standard catalog
programs are flagged ``is_standard``; exceptional programs are ordinary rows
with ``is_standard = false`` (there is no magic "other" record).

``icon`` is a controlled PrimeIcons identifier (CHECK-constrained to a curated
allow-list) used by program cards/navigation. No image uploads or URLs.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Final

from sqlalchemy import Boolean, CheckConstraint, DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.edition import Edition

# Controlled PrimeIcons identifiers (without the "pi pi-" prefix). Mirrored by a
# frontend constant; both constrain the icon picker. CHECK-enforced in the DB.
PROGRAM_ICONS: Final = (
    "github",
    "briefcase",
    "building",
    "heart",
    "users",
    "star",
    "code",
    "graduation-cap",
    "globe",
    "sun",
    "bolt",
    "folder",
)
DEFAULT_PROGRAM_ICON: Final = "folder"

_ICONS_SQL: Final = ", ".join(f"'{i}'" for i in PROGRAM_ICONS)


def slugify(value: str) -> str:
    """Derive a stable, URL-friendly slug from a human name.

    Lowercases, replaces runs of non-alphanumerics with a single hyphen, and
    trims leading/trailing hyphens. Raises ValueError if nothing usable remains.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise ValueError("Cannot derive a slug from the given name.")
    return slug


class Program(Base):
    """A contributor-program catalog entry."""

    __tablename__ = "programs"

    __table_args__ = (
        CheckConstraint(f"icon IN ({_ICONS_SQL})", name="icon_valid"),
        UniqueConstraint("slug", name="uq_programs_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Stable, URL-friendly identifier, unique across programs. Auto-generated
    # from the name on creation and immutable afterwards.
    slug: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(default=None)
    icon: Mapped[str] = mapped_column(String(64), default=DEFAULT_PROGRAM_ICON)
    # True for the seeded standard catalog; false for exceptional programs.
    is_standard: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # NOTE: `onupdate` is applied on ORM flush, not a database trigger.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    editions: Mapped[list[Edition]] = relationship(back_populates="program")
