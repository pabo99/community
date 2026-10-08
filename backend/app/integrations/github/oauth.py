"""GitHub OAuth client.

Encapsulates the authorization-code flow's external calls: building the
authorize URL, exchanging the code for an access token, and fetching the
authenticated user's profile. The token obtained here is ephemeral: it is used
once to read the profile and then discarded (not persisted).

The client is a small, injectable object so tests can substitute a deterministic
fake without any live GitHub call or extra mocking dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"


class GitHubOAuthError(Exception):
    """Raised when a GitHub OAuth exchange or profile fetch fails.

    The message is deliberately sanitized: it never contains the OAuth code,
    access token, or client secret.
    """


@dataclass(frozen=True)
class GitHubUser:
    """Minimal GitHub profile used for identity linking."""

    id: str  # stable numeric id, as string (canonical identifier)
    login: str  # current username (mutable)
    name: str | None  # display name, when present


class GitHubOAuthClient:
    """Performs GitHub OAuth token exchange and profile retrieval."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._scope = scope
        self._timeout = timeout_seconds

    def authorize_url(self, state: str) -> str:
        """Build the GitHub authorize URL for the given opaque state."""
        query = urlencode(
            {
                "client_id": self._client_id,
                "redirect_uri": self._redirect_uri,
                "scope": self._scope,
                "state": state,
                "allow_signup": "true",
            }
        )
        return f"{GITHUB_AUTHORIZE_URL}?{query}"

    def exchange_code(self, code: str) -> str:
        """Exchange an authorization code for an access token.

        Returns the access token string. Raises GitHubOAuthError on failure
        without leaking the code or secret.
        """
        try:
            response = httpx.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "code": code,
                    "redirect_uri": self._redirect_uri,
                },
                headers={"Accept": "application/json"},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:  # network/timeout
            raise GitHubOAuthError("GitHub token exchange request failed") from exc

        if response.status_code != httpx.codes.OK:
            raise GitHubOAuthError("GitHub token exchange returned an error status")

        payload = response.json()
        token = payload.get("access_token")
        if not token:
            # GitHub returns 200 with an "error" field for bad codes.
            raise GitHubOAuthError("GitHub token exchange did not return a token")
        return str(token)

    def fetch_user(self, access_token: str) -> GitHubUser:
        """Fetch the authenticated user's profile using the access token."""
        try:
            response = httpx.get(
                GITHUB_USER_URL,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise GitHubOAuthError("GitHub user request failed") from exc

        if response.status_code != httpx.codes.OK:
            raise GitHubOAuthError("GitHub user request returned an error status")

        payload = response.json()
        user_id = payload.get("id")
        login = payload.get("login")
        if user_id is None or not login:
            raise GitHubOAuthError("GitHub user response missing required fields")

        return GitHubUser(id=str(user_id), login=str(login), name=payload.get("name"))
