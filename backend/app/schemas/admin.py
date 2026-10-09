"""Admin API schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class AdminPingResponse(BaseModel):
    """Confirmation that the caller holds superadmin authorization."""

    status: str
    person_id: uuid.UUID
