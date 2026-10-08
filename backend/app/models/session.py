"""Server-side session and OAuth-state models.

Sessions are PostgreSQL-backed (technical-design.md §6): the browser holds an
opaque high-entropy token; the database stores only its SHA-256 hash, so a
database read cannot reconstruct a usable cookie. Absolute expiration only.

``OAuthState`` is a short-lived, single-use, browser-bound value protecting the
authorization-code flow against CSRF/replay. Its token is also stored hashed.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserSession(Base):
    """An authenticated server-side session for a Person."""

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # SHA-256 hex digest of the opaque session token held by the browser.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        index=True,
    )
    # Double-submit CSRF token bound to this session (opaque, not a secret in
    # the authentication sense; readable by the SPA to echo back on mutations).
    csrf_token: Mapped[str] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OAuthState(Base):
    """A short-lived, single-use OAuth state value bound to one browser."""

    __tablename__ = "oauth_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # SHA-256 hex digest of the state value sent to GitHub (query param).
    state_hash: Mapped[str] = mapped_column(String(64), unique=True)
    # SHA-256 hex digest of a binding token stored in a browser cookie, so the
    # callback must come from the same browser that initiated the flow.
    binding_hash: Mapped[str] = mapped_column(String(64))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
