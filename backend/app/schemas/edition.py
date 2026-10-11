"""Edition API schemas.

Creation uses a year + period; the slug, suggested name, and default dates are
generated server-side. The admin API never accepts ``source``/``external_id``
(manual editions are always ``source=community``) nor ``status`` (status is a
temporal value computed from the dates). ``slug`` is immutable.

The response exposes the computed ``status`` and the read-only provenance.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.edition import EDITION_PERIODS, EDITION_SOURCES, EDITION_STATUSES

EditionPeriod = Literal["annual", "first_semester", "second_semester"]
EditionStatus = Literal["upcoming", "active", "finished"]
EditionSource = Literal["community", "omegaup"]

assert set(EDITION_PERIODS) == set(EditionPeriod.__args__)  # type: ignore[attr-defined]
assert set(EDITION_STATUSES) == set(EditionStatus.__args__)  # type: ignore[attr-defined]
assert set(EDITION_SOURCES) == set(EditionSource.__args__)  # type: ignore[attr-defined]


class EditionCreate(BaseModel):
    """Create an edition from a year + period.

    The slug/name/dates are generated server-side; ``name`` and the dates may be
    overridden here (dates must be ordered when both are provided).
    """

    model_config = ConfigDict(extra="forbid")

    year: int = Field(ge=2000, le=2100)
    period: EditionPeriod = "annual"
    # Optional overrides of the generated suggestions.
    name: str | None = Field(default=None, min_length=1, max_length=255)
    starts_on: datetime.date | None = None
    ends_on: datetime.date | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> EditionCreate:
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("ends_on must be on or after starts_on.")
        return self


class EditionUpdate(BaseModel):
    """Partial update of mutable fields only (name, dates).

    ``slug``/``source``/``external_id`` are immutable and ``status`` is computed;
    none are accepted. Omitted = unchanged; explicit null on a date clears it (it
    will then be revalidated against the resulting range).
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    starts_on: datetime.date | None = None
    ends_on: datetime.date | None = None

    def provided_fields(self) -> set[str]:
        return set(self.model_fields_set)


class EditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    program_id: uuid.UUID
    slug: str
    name: str
    period: EditionPeriod
    status: EditionStatus
    starts_on: datetime.date
    ends_on: datetime.date
    source: EditionSource
    external_id: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
