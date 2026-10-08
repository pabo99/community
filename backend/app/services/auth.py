"""Authentication service: OAuth state lifecycle, login, and sessions.

This service owns the transaction boundaries for authentication. Repositories
stage changes; the service commits once per unit of work.

Concurrency: two simultaneous first-time logins for the same new GitHub id can
both miss the initial lookup and race to insert. The partial unique index on
``(provider, provider_user_id)`` guarantees one wins; the loser raises a unique
violation, which we catch (narrowly) inside a SAVEPOINT and resolve by
re-reading the now-existing row.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.tokens import generate_token, hash_token, tokens_equal
from app.config import Settings
from app.integrations.github.oauth import GitHubUser
from app.models.external_identity import PROVIDER_GITHUB, ExternalIdentity
from app.models.person import Person
from app.models.session import UserSession
from app.repositories.identity import IdentityRepository
from app.repositories.session import SessionRepository


@dataclass(frozen=True)
class IssuedState:
    """A freshly issued OAuth state and its browser-binding token."""

    state: str  # goes to GitHub as the `state` query parameter
    binding: str  # stored in an HttpOnly cookie on the initiating browser


@dataclass(frozen=True)
class IssuedSession:
    """A freshly issued session: the raw cookie token and its CSRF token."""

    token: str
    csrf_token: str
    person: Person


class AuthService:
    """Coordinates GitHub OAuth login and server-side sessions."""

    def __init__(self, session: Session, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._identities = IdentityRepository(session)
        self._sessions = SessionRepository(session)

    # --- OAuth state ---------------------------------------------------------

    def issue_oauth_state(self) -> IssuedState:
        """Create a single-use, short-lived, browser-bound OAuth state."""
        state = generate_token()
        binding = generate_token()
        expires_at = datetime.now(UTC) + timedelta(seconds=self._settings.oauth_state_ttl_seconds)
        # Opportunistically clear expired states to bound table growth.
        self._sessions.delete_expired_oauth_states(datetime.now(UTC))
        self._sessions.create_oauth_state(
            state_hash=hash_token(state),
            binding_hash=hash_token(binding),
            expires_at=expires_at,
        )
        self._session.commit()
        return IssuedState(state=state, binding=binding)

    def consume_oauth_state(self, *, state: str | None, binding: str | None) -> bool:
        """Atomically consume an OAuth state, validating binding and expiry.

        Returns True only if the state exists, matches the browser binding, and
        has not expired. The row is always deleted on first touch (single-use),
        so a replay of the same state fails.
        """
        if not state or not binding:
            return False

        record = self._sessions.pop_oauth_state(hash_token(state))
        if record is None:
            self._session.commit()
            return False

        valid = record.expires_at > datetime.now(UTC) and tokens_equal(
            record.binding_hash, hash_token(binding)
        )
        # The pop already staged a delete; commit it regardless (single-use).
        self._session.commit()
        return valid

    # --- Login ---------------------------------------------------------------

    def login_with_github(self, github_user: GitHubUser) -> IssuedSession:
        """Find or create the Person+GitHub identity, then issue a session.

        Transaction-safe and concurrency-safe. Commits once on success; rolls
        back on unexpected failure, leaving no partial identity or session.
        """
        try:
            person = self._resolve_github_person(github_user)
            issued = self._create_session(person)
            self._session.commit()
            return issued
        except Exception:
            self._session.rollback()
            raise

    def _resolve_github_person(self, github_user: GitHubUser) -> Person:
        existing = self._identities.get_by_provider_identifier(PROVIDER_GITHUB, github_user.id)
        if existing is not None:
            self._update_identity(existing.person, existing, github_user)
            return existing.person

        # Not found: attempt to create inside a SAVEPOINT so a concurrent
        # inserter's unique violation does not poison the outer transaction.
        try:
            with self._session.begin_nested():
                person = self._identities.create_person(display_name=github_user.name)
                self._identities.add_identity(
                    person=person,
                    provider=PROVIDER_GITHUB,
                    provider_user_id=github_user.id,
                    username=github_user.login,
                    verified_at=datetime.now(UTC),
                )
                self._session.flush()
            return person
        except IntegrityError:
            # A concurrent login created it first. Re-read the now-present row.
            winner = self._identities.get_by_provider_identifier(PROVIDER_GITHUB, github_user.id)
            if winner is None:  # pragma: no cover - defensive
                raise
            self._update_identity(winner.person, winner, github_user)
            return winner.person

    def _update_identity(
        self, person: Person, identity: ExternalIdentity, github_user: GitHubUser
    ) -> None:
        # Keep the mutable username fresh; refresh verification timestamp.
        identity.username = github_user.login
        identity.verified_at = datetime.now(UTC)
        # Set display_name from GitHub only when we don't already have one, so
        # user-maintained profile data is not overwritten unnecessarily.
        if not person.display_name and github_user.name:
            person.display_name = github_user.name

    def _create_session(self, person: Person) -> IssuedSession:
        token = generate_token()
        csrf_token = generate_token()
        expires_at = datetime.now(UTC) + timedelta(seconds=self._settings.session_ttl_seconds)
        self._sessions.create_session(
            token_hash=hash_token(token),
            person_id=person.id,
            csrf_token=csrf_token,
            expires_at=expires_at,
        )
        return IssuedSession(token=token, csrf_token=csrf_token, person=person)

    # --- Logout --------------------------------------------------------------

    def logout(self, user_session: UserSession) -> None:
        self._sessions.delete_session(user_session)
        self._session.commit()
