"""Opaque token generation and hashing.

Raw tokens are high-entropy and live only in the browser. Only their SHA-256
hex digests are persisted, so a database read cannot reconstruct a usable
cookie. Comparisons use constant-time equality.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

# 32 bytes -> 43-char urlsafe token; ample entropy for session/state/csrf.
_TOKEN_NBYTES = 32


def generate_token() -> str:
    """Return a new cryptographically random urlsafe token."""
    return secrets.token_urlsafe(_TOKEN_NBYTES)


def hash_token(token: str) -> str:
    """Return the SHA-256 hex digest of a token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_equal(left: str, right: str) -> bool:
    """Constant-time comparison of two tokens/digests."""
    return hmac.compare_digest(left, right)
