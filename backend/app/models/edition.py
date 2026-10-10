"""Edition domain model.

An Edition is a concrete occurrence of a Program, e.g. "GSoC 2027"
(product-design.md §3). An Edition owns one or more Projects.

Provenance (product-design.md §21.4, technical-design.md §19): most editions are
Community-managed; some future GSoC editions may be projected from omegaUp. The
``source`` field records origin and ``external_id`` carries the stable upstream
identifier when the source is not Community-native. No omegaUp API call or
synchronization is implemented here — only the columns and constraints so a
later integration does not require a disruptive schema change. Community-native
editions never require omegaUp connectivity.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Final

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.program import Program
    from app.models.project import Project

# Lifecycle status.
EDITION_STATUS_DRAFT: Final = "draft"
EDITION_STATUS_OPEN: Final = "open"
EDITION_STATUS_IN_PROGRESS: Final = "in_progress"
EDITION_STATUS_COMPLETED: Final = "completed"
EDITION_STATUS_ARCHIVED: Final = "archived"
EDITION_STATUSES: Final = (
    EDITION_STATUS_DRAFT,
    EDITION_STATUS_OPEN,
    EDITION_STATUS_IN_PROGRESS,
    EDITION_STATUS_COMPLETED,
    EDITION_STATUS_ARCHIVED,
)

# Provenance / source of truth for the edition.
EDITION_SOURCE_COMMUNITY: Final = "community"
EDITION_SOURCE_OMEGAUP: Final = "omegaup"
EDITION_SOURCES: Final = (EDITION_SOURCE_COMMUNITY, EDITION_SOURCE_OMEGAUP)

_STATUSES_SQL: Final = ", ".join(f"'{s}'" for s in EDITION_STATUSES)
_SOURCES_SQL: Final = ", ".join(f"'{s}'" for s in EDITION_SOURCES)


class Edition(Base):
    """A concrete occurrence of a Program."""

    __tablename__ = "editions"

    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUSES_SQL})", name="status_valid"),
        CheckConstraint(f"source IN ({_SOURCES_SQL})", name="source_valid"),
        # Date boundaries, when both present, must be ordered.
        CheckConstraint(
            "starts_on IS NULL OR ends_on IS NULL OR ends_on >= starts_on",
            name="dates_ordered",
        ),
        # A Community-native edition has no external id; a non-community source
        # must carry a non-empty external id.
        CheckConstraint(
            "(source = 'community' AND external_id IS NULL) "
            "OR (source <> 'community' AND external_id IS NOT NULL "
            "AND length(external_id) > 0)",
            name="external_id_matches_source",
        ),
        # Slugs are unique within a program (e.g. "2027" per program).
        UniqueConstraint("program_id", "slug", name="uq_editions_program_id_slug"),
        # A given upstream edition maps to exactly one Community edition.
        Index(
            "uq_editions_source_external_id",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        # Preserve history: deleting a program with editions is rejected.
        ForeignKey("programs.id", ondelete="RESTRICT"),
        index=True,
    )

    slug: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default=EDITION_STATUS_DRAFT)

    starts_on: Mapped[date | None] = mapped_column(Date, default=None)
    ends_on: Mapped[date | None] = mapped_column(Date, default=None)

    source: Mapped[str] = mapped_column(String(32), default=EDITION_SOURCE_COMMUNITY)
    # Stable upstream identifier when the edition is not Community-native.
    external_id: Mapped[str | None] = mapped_column(String(255), default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # NOTE: `onupdate` is applied on ORM flush, not a database trigger.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    program: Mapped[Program] = relationship(back_populates="editions")
    projects: Mapped[list[Project]] = relationship(back_populates="edition")
