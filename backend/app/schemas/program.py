"""Program API schemas.

Explicit request/response contracts; ORM models are never exposed directly.
The slug is auto-generated from the name on creation and is immutable, so it is
not accepted on create or update. ``kind`` is removed (the catalog is the set of
categories). ``icon`` is a controlled PrimeIcons identifier.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.program import PROGRAM_ICONS

ProgramIcon = Literal[
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
]

# Keep the Literal in sync with the model's allow-list.
assert set(PROGRAM_ICONS) == set(ProgramIcon.__args__)  # type: ignore[attr-defined]


class ProgramCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    icon: ProgramIcon = "folder"


class ProgramUpdate(BaseModel):
    """Partial update of editable fields. Slug is immutable and not accepted."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    icon: ProgramIcon | None = None


class ActiveEditionSummary(BaseModel):
    """Minimal reference to an active edition, for the Programs table."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str


class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    description: str | None
    icon: str
    is_standard: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ProgramListItem(ProgramResponse):
    """Program row enriched for the admin table: edition count + active editions."""

    edition_count: int
    active_editions: list[ActiveEditionSummary]
