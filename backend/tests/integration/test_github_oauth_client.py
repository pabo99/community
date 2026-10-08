"""Unit tests for the GitHub OAuth client (no live GitHub, httpx mocked)."""

from __future__ import annotations

import httpx
import pytest
from app.integrations.github.oauth import (
    GITHUB_AUTHORIZE_URL,
    GitHubOAuthClient,
    GitHubOAuthError,
)


def _client() -> GitHubOAuthClient:
    return GitHubOAuthClient(
        client_id="cid",
        client_secret="secret",
        redirect_uri="http://localhost:5173/api/auth/github/callback",
        scope="read:user",
    )


def test_authorize_url_includes_state_and_scope() -> None:
    url = _client().authorize_url("abc123")
    assert url.startswith(GITHUB_AUTHORIZE_URL)
    assert "state=abc123" in url
    assert "scope=read%3Auser" in url
    assert "client_id=cid" in url
    # The client secret must never appear in the authorize URL.
    assert "secret" not in url


def test_exchange_code_returns_token(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(200, json={"access_token": "gho_token"})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert _client().exchange_code("code123") == "gho_token"


def test_exchange_code_error_payload_raises_sanitized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(200, json={"error": "bad_verification_code"})

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(GitHubOAuthError) as exc:
        _client().exchange_code("code123")
    # Error message does not leak the code.
    assert "code123" not in str(exc.value)


def test_fetch_user_parses_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(200, json={"id": 42, "login": "octocat", "name": "The Octocat"})

    monkeypatch.setattr(httpx, "get", fake_get)
    user = _client().fetch_user("gho_token")
    assert user.id == "42"
    assert user.login == "octocat"
    assert user.name == "The Octocat"


def test_fetch_user_missing_fields_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        return httpx.Response(200, json={"id": 42})

    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(GitHubOAuthError):
        _client().fetch_user("gho_token")
