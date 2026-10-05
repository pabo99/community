"""Health endpoint response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    """Process liveness payload.

    Liveness reflects only that the process is up and does not depend on the
    database or external services (technical-design.md §13).
    """

    status: str = "alive"
