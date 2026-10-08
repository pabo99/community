"""Persistence for server-side sessions and OAuth states.

All tokens are stored as SHA-256 hex digests; raw tokens live only in the
browser. Methods never commit; the caller owns the transaction boundary.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.session import OAuthState, UserSession


class SessionRepository:
    """Data access for UserSession and OAuthState."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- OAuth state ---------------------------------------------------------

    def create_oauth_state(
        self,
        *,
        state_hash: str,
        binding_hash: str,
        expires_at: datetime,
    ) -> OAuthState:
        state = OAuthState(
            state_hash=state_hash,
            binding_hash=binding_hash,
            expires_at=expires_at,
        )
        self._session.add(state)
        return state

    def pop_oauth_state(self, state_hash: str) -> OAuthState | None:
        """Fetch and delete an OAuth state atomically (single-use).

        Returns the row if it existed (deleting it in the same transaction), or
        ``None``. Expiry is validated by the caller.
        """
        stmt = select(OAuthState).where(OAuthState.state_hash == state_hash)
        state = self._session.scalars(stmt).one_or_none()
        if state is not None:
            self._session.delete(state)
            self._session.flush()
        return state

    def delete_expired_oauth_states(self, now: datetime) -> None:
        self._session.execute(delete(OAuthState).where(OAuthState.expires_at <= now))

    # --- Sessions ------------------------------------------------------------

    def create_session(
        self,
        *,
        token_hash: str,
        person_id: uuid.UUID,
        csrf_token: str,
        expires_at: datetime,
    ) -> UserSession:
        user_session = UserSession(
            token_hash=token_hash,
            person_id=person_id,
            csrf_token=csrf_token,
            expires_at=expires_at,
        )
        self._session.add(user_session)
        return user_session

    def get_by_token_hash(self, token_hash: str) -> UserSession | None:
        stmt = select(UserSession).where(UserSession.token_hash == token_hash)
        return self._session.scalars(stmt).one_or_none()

    def delete_session(self, user_session: UserSession) -> None:
        self._session.delete(user_session)

    def flush(self) -> None:
        self._session.flush()
