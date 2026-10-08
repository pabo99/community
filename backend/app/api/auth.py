"""Authentication API: GitHub OAuth login, callback, and logout.

The flow uses an opaque, single-use, browser-bound OAuth state and issues a
PostgreSQL-backed server-side session. Redirect destinations are always taken
from trusted configuration, never from request parameters.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.cookies import (
    OAUTH_BINDING_COOKIE,
    clear_csrf_cookie,
    clear_oauth_binding_cookie,
    clear_session_cookie,
    set_csrf_cookie,
    set_oauth_binding_cookie,
    set_session_cookie,
)
from app.auth.dependencies import get_current_session, require_csrf
from app.config import Settings, get_settings
from app.db.session import get_db
from app.integrations.github.oauth import GitHubOAuthClient, GitHubOAuthError
from app.models.session import UserSession
from app.services.auth import AuthService

logger = logging.getLogger("app.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_github_oauth_client(
    settings: Settings = Depends(get_settings),
) -> GitHubOAuthClient:
    """Build the GitHub OAuth client, failing closed if unconfigured.

    The error is sanitized and never includes any secret value.
    """
    if not settings.github_oauth_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub authentication is not configured.",
        )
    return GitHubOAuthClient(
        client_id=settings.github_oauth_client_id or "",
        client_secret=settings.github_oauth_client_secret or "",
        redirect_uri=settings.github_oauth_redirect_uri,
        scope=settings.github_oauth_scope,
    )


@router.get("/github/login")
def github_login(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    github: GitHubOAuthClient = Depends(get_github_oauth_client),
) -> Response:
    """Begin GitHub OAuth: issue state, bind the browser, redirect to GitHub."""
    service = AuthService(db, settings)
    issued = service.issue_oauth_state()

    response = RedirectResponse(
        url=github.authorize_url(issued.state),
        status_code=status.HTTP_302_FOUND,
    )
    set_oauth_binding_cookie(response, settings, issued.binding)
    return response


@router.get("/github/callback")
def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    github: GitHubOAuthClient = Depends(get_github_oauth_client),
) -> Response:
    """Complete GitHub OAuth: validate state, create session, redirect home."""
    service = AuthService(db, settings)

    binding = request.cookies.get(OAUTH_BINDING_COOKIE)
    # Consume the state atomically (single-use) before any token exchange.
    if not service.consume_oauth_state(state=state, binding=binding):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state.",
        )

    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing authorization code.",
        )

    try:
        access_token = github.exchange_code(code)
        github_user = github.fetch_user(access_token)
    except GitHubOAuthError:
        # Do not include OAuth code/token/secret in the response or logs.
        logger.warning("GitHub OAuth exchange failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub authentication failed.",
        ) from None

    issued = service.login_with_github(github_user)

    response = RedirectResponse(
        url=settings.frontend_post_login_url,
        status_code=status.HTTP_302_FOUND,
    )
    set_session_cookie(response, settings, issued.token)
    set_csrf_cookie(response, settings, issued.csrf_token)
    clear_oauth_binding_cookie(response, settings)
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    user_session: UserSession = Depends(get_current_session),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _csrf: None = Depends(require_csrf),
) -> Response:
    """Invalidate the current session (CSRF-protected)."""
    service = AuthService(db, settings)
    service.logout(user_session)

    response.status_code = status.HTTP_204_NO_CONTENT
    clear_session_cookie(response, settings)
    clear_csrf_cookie(response, settings)
    return response
