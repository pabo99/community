"""User-facing auth schemas.

Explicit response contracts; ORM models are never returned directly. Only safe
profile fields are exposed — never tokens, hashes, or internal columns.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class MeResponse(BaseModel):
    """The authenticated user's safe profile.

    ``is_superadmin`` is the minimal platform-role information the frontend
    needs for authorization UX. Backend authorization remains authoritative.
    """

    id: uuid.UUID
    display_name: str | None
    github_username: str | None
    is_superadmin: bool = False
