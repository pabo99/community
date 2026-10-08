"""Request-scoped authentication and CSRF dependencies.

``get_current_person`` resolves the server-side session from the opaque cookie
and returns the authenticated Person, or raises 401. ``require_csrf`` enforces
the double-submit CSRF pattern for authenticated mutations (reusable beyond
logout).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.tokens import hash_token, tokens_equal
from app.config import Settings, get_settings
from app.db.session import get_db
from app.models.person import Person
from app.models.session import UserSession
from app.repositories.session import SessionRepository


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Cookie"},
    )


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UserSession:
    """Return the valid, unexpired UserSession for the request, or 401."""
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise _unauthorized()

    repo = SessionRepository(db)
    user_session = repo.get_by_token_hash(hash_token(token))
    if user_session is None:
        raise _unauthorized()

    if user_session.expires_at <= datetime.now(UTC):
        # Expired: clean up and treat as anonymous.
        repo.delete_session(user_session)
        raise _unauthorized()

    return user_session


def get_current_person(
    user_session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
) -> Person:
    """Return the authenticated Person, or 401 if anonymous/invalid."""
    person = db.get(Person, user_session.person_id)
    if person is None:
        raise _unauthorized()
    return person


def require_csrf(
    request: Request,
    user_session: UserSession = Depends(get_current_session),
    settings: Settings = Depends(get_settings),
) -> None:
    """Enforce double-submit CSRF for authenticated mutations.

    The client must send the CSRF token (from the readable CSRF cookie) in the
    configured header; it must match the token bound to the session. This does
    not rely on SameSite alone.
    """
    header_token = request.headers.get(settings.csrf_header_name)
    if not header_token or not tokens_equal(header_token, user_session.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )
