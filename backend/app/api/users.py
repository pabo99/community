"""User profile API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_person
from app.db.session import get_db
from app.models.external_identity import PROVIDER_GITHUB
from app.models.person import Person
from app.repositories.identity import IdentityRepository
from app.schemas.user import MeResponse

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/me", response_model=MeResponse)
def read_me(
    person: Person = Depends(get_current_person),
    db: Session = Depends(get_db),
) -> MeResponse:
    """Return the authenticated user's safe profile."""
    identities = IdentityRepository(db).list_identities_for_person(person.id)
    github_username = next(
        (i.username for i in identities if i.provider == PROVIDER_GITHUB),
        None,
    )
    return MeResponse(
        id=person.id,
        display_name=person.display_name,
        github_username=github_username,
    )
