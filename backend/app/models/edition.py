"""Edition domain model.

An Edition is a concrete occurrence of a Program for a calendar period, e.g.
"GSoC 2026" (product-design.md §3). An Edition owns one or more Projects.

Identity is a calendar-period slug:
- annual:          ``2026``   (Jan 1 - Dec 31)
- first semester:  ``2026-1`` (Jan 1 - Jun 30)
- second semester: ``2026-2`` (Jul 1 - Dec 31)

The slug is the single source of truth for the period; the period is derived
from it, not stored. ``starts_on``/``ends_on`` default from the period and are
editable (GSoC's real activity window differs from the calendar year).

Status is NOT stored. It is a temporal status computed from the dates relative
to a documented reference date (UTC "today", see ``compute_status``):
- ``upcoming``:  today < starts_on
- ``active``:    starts_on <= today <= ends_on (inclusive)
- ``finished``:  today > ends_on

Provenance: ``source`` records origin. Manually created editions are always
``community``; only a future trusted omegaUp integration may create/update
``omegaup`` records with authoritative ``external_id`` values. No sync here.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Final, Literal

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

# Calendar period of an edition (derived from the slug; not stored).
PERIOD_ANNUAL: Final = "annual"
PERIOD_FIRST_SEMESTER: Final = "first_semester"
PERIOD_SECOND_SEMESTER: Final = "second_semester"
EDITION_PERIODS: Final = (PERIOD_ANNUAL, PERIOD_FIRST_SEMESTER, PERIOD_SECOND_SEMESTER)
EditionPeriod = Literal["annual", "first_semester", "second_semester"]

# Temporal status (computed; not stored).
STATUS_UPCOMING: Final = "upcoming"
STATUS_ACTIVE: Final = "active"
STATUS_FINISHED: Final = "finished"
EDITION_STATUSES: Final = (STATUS_UPCOMING, STATUS_ACTIVE, STATUS_FINISHED)
EditionStatus = Literal["upcoming", "active", "finished"]

# Provenance.
EDITION_SOURCE_COMMUNITY: Final = "community"
EDITION_SOURCE_OMEGAUP: Final = "omegaup"
EDITION_SOURCES: Final = (EDITION_SOURCE_COMMUNITY, EDITION_SOURCE_OMEGAUP)

_SOURCES_SQL: Final = ", ".join(f"'{s}'" for s in EDITION_SOURCES)

_SLUG_RE: Final = re.compile(r"^(?P<year>\d{4})(?:-(?P<period>[12]))?$")


class InvalidEditionSlugError(ValueError):
    """Raised when an edition slug does not encode a valid calendar period."""


def period_of_slug(slug: str) -> EditionPeriod:
    """Return the calendar period encoded by an edition slug.

    Raises InvalidEditionSlugError if the slug is not ``YYYY``/``YYYY-1``/
    ``YYYY-2`` (used to fail clearly rather than invent a period).
    """
    match = _SLUG_RE.match(slug)
    if not match:
        raise InvalidEditionSlugError(f"Edition slug '{slug}' is not a valid calendar period.")
    suffix = match.group("period")
    if suffix is None:
        return PERIOD_ANNUAL
    return PERIOD_FIRST_SEMESTER if suffix == "1" else PERIOD_SECOND_SEMESTER


def slug_for(year: int, period: EditionPeriod) -> str:
    """Build an edition slug from a year and period."""
    if period == PERIOD_ANNUAL:
        return f"{year}"
    return f"{year}-{'1' if period == PERIOD_FIRST_SEMESTER else '2'}"


def default_dates(year: int, period: EditionPeriod) -> tuple[date, date]:
    """Return the default (starts_on, ends_on) for a year and period."""
    if period == PERIOD_FIRST_SEMESTER:
        return date(year, 1, 1), date(year, 6, 30)
    if period == PERIOD_SECOND_SEMESTER:
        return date(year, 7, 1), date(year, 12, 31)
    return date(year, 1, 1), date(year, 12, 31)


def default_dates_for_slug(slug: str) -> tuple[date, date]:
    """Return default dates for an edition slug (fails clearly on bad slugs)."""
    match = _SLUG_RE.match(slug)
    if not match:
        raise InvalidEditionSlugError(f"Edition slug '{slug}' is not a valid calendar period.")
    year = int(match.group("year"))
    return default_dates(year, period_of_slug(slug))


def today_utc() -> date:
    """Reference 'today' for temporal status: the current UTC calendar date."""
    return datetime.now(UTC).date()


def compute_status(
    starts_on: date, ends_on: date, *, reference: date | None = None
) -> EditionStatus:
    """Compute temporal status from the date range vs. the reference date."""
    ref = reference or today_utc()
    if ref < starts_on:
        return STATUS_UPCOMING
    if ref > ends_on:
        return STATUS_FINISHED
    return STATUS_ACTIVE


class Edition(Base):
    """A concrete occurrence of a Program for a calendar period."""

    __tablename__ = "editions"

    __table_args__ = (
        CheckConstraint(f"source IN ({_SOURCES_SQL})", name="source_valid"),
        CheckConstraint("ends_on >= starts_on", name="dates_ordered"),
        # A community edition has no external id; a non-community source must
        # carry a non-empty external id (future-integration invariant).
        CheckConstraint(
            "(source = 'community' AND external_id IS NULL) "
            "OR (source <> 'community' AND external_id IS NOT NULL "
            "AND length(external_id) > 0)",
            name="external_id_matches_source",
        ),
        UniqueConstraint("program_id", "slug", name="uq_editions_program_id_slug"),
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
        ForeignKey("programs.id", ondelete="RESTRICT"),
        index=True,
    )

    slug: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    # Dates are required: temporal status is derived from them.
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)

    source: Mapped[str] = mapped_column(String(32), default=EDITION_SOURCE_COMMUNITY)
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

    @property
    def period(self) -> EditionPeriod:
        return period_of_slug(self.slug)

    @property
    def status(self) -> EditionStatus:
        return compute_status(self.starts_on, self.ends_on)
