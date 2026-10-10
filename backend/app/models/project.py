"""Project domain model.

A Project is a unit of work within an Edition (product-design.md §3). Interns
and residents normally work on a project; GSoC candidates may relate to several.
Project is the scope that M1-07b mentor assignments attach to.

A Project is distinct from an external GSoC *idea* (product-design.md §21.2):
there is no one-to-one relationship and no idea linkage is modeled here. A
future idea↔project association can be added without reshaping this model.

Repository linkage (e.g. to omegaup/omegaup) is intentionally not modeled yet:
multiple projects may reference the same repository, so a shared repository
relationship will be modeled separately when needed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.edition import Edition


class Project(Base):
    """A unit of work within an Edition."""

    __tablename__ = "projects"

    __table_args__ = (
        # Slugs are unique within an edition.
        UniqueConstraint("edition_id", "slug", name="uq_projects_edition_id_slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    edition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # Preserve history: deleting an edition with projects is rejected.
        ForeignKey("editions.id", ondelete="RESTRICT"),
        index=True,
    )

    slug: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # NOTE: `onupdate` is applied on ORM flush, not a database trigger.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    edition: Mapped[Edition] = relationship(back_populates="projects")
