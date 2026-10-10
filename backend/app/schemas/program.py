"""Program API schemas.

Explicit request/response contracts; ORM models are never exposed directly.
``slug`` is immutable after creation, so ``ProgramUpdate`` does not accept it;
sending ``slug`` is rejected (``extra="forbid"``) rather than silently ignored.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.program import PROGRAM_KINDS

ProgramKind = Literal["gsoc", "internship", "residency", "volunteer", "other"]

# Keep the Literal in sync with the model's controlled vocabulary.
assert set(PROGRAM_KINDS) == set(ProgramKind.__args__)  # type: ignore[attr-defined]

_SLUG_PATTERN = r"^[a-z0-9][a-z0-9-]*$"


class ProgramCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=1, max_length=64, pattern=_SLUG_PATTERN)
    name: str = Field(min_length=1, max_length=255)
    kind: ProgramKind
    description: str | None = None


class ProgramUpdate(BaseModel):
    """Partial update. Omitted fields are left unchanged.

    ``slug`` is immutable and intentionally absent; ``extra="forbid"`` makes a
    request that includes ``slug`` (or any unknown field) fail with 422 rather
    than silently ignoring it.
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    kind: ProgramKind | None = None
    description: str | None = None


class ProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    kind: str
    description: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
