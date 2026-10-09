"""Administrative API (superadmin only).

Minimal at M1-07: a single protected endpoint to verify the authorization
foundation end-to-end (401 anonymous, 403 authenticated non-admin, 200
superadmin). The mentor-request inbox is a follow-on feature (M1-07b).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.auth.authz import require_superadmin
from app.models.person import Person
from app.schemas.admin import AdminPingResponse

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/ping", response_model=AdminPingResponse)
def admin_ping(person: Person = Depends(require_superadmin)) -> AdminPingResponse:
    """Return ok for an authenticated superadmin; 401/403 otherwise."""
    return AdminPingResponse(status="ok", person_id=person.id)
