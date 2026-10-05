"""Health endpoint response schemas."""

from __future__ import annotations

from pydantic import BaseModel


class LivenessResponse(BaseModel):
    """Process liveness payload.

    Liveness reflects only that the process is up and does not depend on the
    database or external services (technical-design.md §13).
    """

    status: str = "alive"


class ReadinessResponse(BaseModel):
    """Readiness payload.

    Readiness reflects required local dependencies only (PostgreSQL). External
    services (GitHub/omegaUp) never affect readiness (technical-design.md §13).
    The payload is a stable, opaque status and never exposes connection
    strings, hostnames, credentials, or driver details.
    """

    status: str
    database: str
