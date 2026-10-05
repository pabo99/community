"""Health check routes.

``/health/live`` reports process liveness only and must not depend on the
database or external services (technical-design.md §13). Readiness
(``/health/ready``) is introduced with the database foundation in M1-03.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.health import LivenessResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=LivenessResponse)
def liveness() -> LivenessResponse:
    """Return process liveness."""
    return LivenessResponse(status="alive")
