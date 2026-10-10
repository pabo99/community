"""Edition API schemas.

Explicit request/response contracts. ``slug``, ``source``, and ``external_id``
are immutable after creation, so ``EditionUpdate`` does not accept them;
``extra="forbid"`` makes an attempt to change them fail with 422.

PATCH semantics distinguish an omitted field (leave unchanged) from an explicit
``null`` (clear the value) via ``model_fields_set`` — see ``EditionUpdate``.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.edition import EDITION_SOURCES, EDITION_STATUSES

EditionStatus = Literal["draft", "open", "in_progress", "completed", "archived"]
EditionSource = Literal["community", "omegaup"]

# Keep the Literals in sync with the model's controlled vocabularies.
assert set(EDITION_STATUSES) == set(EditionStatus.__args__)  # type: ignore[attr-defined]
assert set(EDITION_SOURCES) == set(EditionSource.__args__)  # type: ignore[attr-defined]

_SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]*$"


def _validate_provenance(source: str, external_id: str | None) -> None:
    """Enforce the community/omegaUp provenance rule (mirrors the DB CHECK)."""
    if source == "community":
        if external_id is not None:
            raise ValueError("A community edition must not have an external_id.")
    else:
        if not external_id:
            raise ValueError(f"A '{source}' edition requires a non-empty external_id.")


def _validate_dates(starts_on: datetime.date | None, ends_on: datetime.date | None) -> None:
    if starts_on is not None and ends_on is not None and ends_on < starts_on:
        raise ValueError("ends_on must be on or after starts_on.")


class EditionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=1, max_length=64, pattern=_SLUG_PATTERN)
    name: str = Field(min_length=1, max_length=255)
    status: EditionStatus = "draft"
    starts_on: datetime.date | None = None
    ends_on: datetime.date | None = None
    source: EditionSource = "community"
    external_id: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _check(self) -> EditionCreate:
        _validate_provenance(self.source, self.external_id)
        _validate_dates(self.starts_on, self.ends_on)
        return self


class EditionUpdate(BaseModel):
    """Partial update of mutable fields only (name, status, dates).

    ``slug``, ``source``, and ``external_id`` are immutable; ``extra="forbid"``
    rejects them. The combined date range is validated against the resulting
    state in the service (an omitted date must keep its stored value, while an
    explicit null clears it) — see ``provided_fields``.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: EditionStatus | None = None
    starts_on: datetime.date | None = None
    ends_on: datetime.date | None = None

    def provided_fields(self) -> set[str]:
        """Field names explicitly present in the request (PATCH semantics)."""
        return set(self.model_fields_set)


class EditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    program_id: uuid.UUID
    slug: str
    name: str
    status: str
    starts_on: datetime.date | None
    ends_on: datetime.date | None
    source: str
    external_id: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
