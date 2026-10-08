"""Cookie helpers for session, OAuth-state binding, and CSRF cookies.

Centralizes cookie attributes so security settings are consistent and
environment-appropriate: HttpOnly session/binding cookies, SameSite=Lax, and
Secure only in production (relaxed for local HTTP development).
"""

from __future__ import annotations

from fastapi import Response

from app.config import Settings

# Name of the short-lived cookie binding an OAuth flow to one browser.
OAUTH_BINDING_COOKIE = "community_oauth_binding"


def set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def set_oauth_binding_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=OAUTH_BINDING_COOKIE,
        value=token,
        max_age=settings.oauth_state_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_oauth_binding_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=OAUTH_BINDING_COOKIE,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def set_csrf_cookie(response: Response, settings: Settings, csrf_token: str) -> None:
    # NOT HttpOnly: the SPA reads this value to echo it back in a request header
    # (double-submit CSRF). It is useless without the HttpOnly session cookie.
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=settings.session_ttl_seconds,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_csrf_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
