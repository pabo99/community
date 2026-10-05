"""Health check routes.

``/health/live`` reports process liveness only and must not depend on the
database or external services. ``/health/ready`` verifies required local
dependencies (PostgreSQL) only, never external services (technical-design.md
§13).
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.db.health import database_is_available
from app.schemas.health import LivenessResponse, ReadinessResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LivenessResponse)
def liveness() -> LivenessResponse:
    """Return process liveness. Never touches the database."""
    return LivenessResponse(status="alive")


@router.get("/ready", response_model=ReadinessResponse)
def readiness(response: Response) -> ReadinessResponse:
    """Return readiness based solely on PostgreSQL availability.

    Returns 200 with ``database: ok`` when PostgreSQL is reachable, otherwise
    503 with ``database: unavailable``. The response never includes exception
    details, connection strings, hostnames, or credentials.
    """
    if database_is_available():
        return ReadinessResponse(status="ready", database="ok")

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(status="not_ready", database="unavailable")
