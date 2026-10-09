"""Authorization dependencies.

Authentication (who you are) is handled by ``get_current_person`` (401 when
anonymous). Authorization (what you may do) is enforced here: an authenticated
but unauthorized user receives 403. The backend is authoritative; frontend
guards are UX only.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_person
from app.db.session import get_db
from app.models.person import Person
from app.repositories.role import RoleRepository


def require_superadmin(
    person: Person = Depends(get_current_person),
    db: Session = Depends(get_db),
) -> Person:
    """Return the current person if they are a platform superadmin, else 403."""
    if not RoleRepository(db).is_superadmin(person.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin privileges required.",
        )
    return person
