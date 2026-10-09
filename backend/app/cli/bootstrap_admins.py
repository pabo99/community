"""Idempotent superadmin bootstrap.

Grants the platform ``superadmin`` role to the Persons whose GitHub identity
matches a configured IMMUTABLE numeric GitHub user id (``SUPERADMIN_GITHUB_IDS``).

Properties:
- Keyed on the immutable GitHub numeric id, never the mutable username.
- Idempotent and safe to rerun: an existing grant is a no-op.
- Only touches the ``superadmin`` role for the configured ids; never modifies
  other roles, persons, or identities.
- Skips (with a message) any configured id that has no identity yet: the user
  must have signed in at least once so a verified Person+identity exists. No
  Person is fabricated.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.engine import get_sessionmaker
from app.models.external_identity import PROVIDER_GITHUB
from app.models.platform_role import ROLE_SUPERADMIN
from app.repositories.identity import IdentityRepository
from app.repositories.role import RoleRepository


@contextmanager
def _session_scope() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def bootstrap_admins(
    session: Session,
    github_ids: list[str],
    *,
    log: Callable[[str], None] = print,
) -> int:
    """Grant superadmin to each configured GitHub id. Returns grants applied.

    Commits once at the end. Each grant is attempted inside a SAVEPOINT so a
    concurrent/duplicate grant hitting the unique constraint is absorbed
    (idempotent) without poisoning the transaction.
    """
    if not github_ids:
        log("No SUPERADMIN_GITHUB_IDS configured; nothing to do.")
        return 0

    identities = IdentityRepository(session)
    roles = RoleRepository(session)
    granted = 0

    for github_id in github_ids:
        identity = identities.get_by_provider_identifier(PROVIDER_GITHUB, github_id)
        if identity is None:
            log(
                f"GitHub id {github_id}: no identity found "
                "(user must sign in once first); skipping."
            )
            continue

        person_id = identity.person_id
        if roles.is_superadmin(person_id):
            log(f"GitHub id {github_id}: already superadmin; no change.")
            continue

        try:
            with session.begin_nested():
                roles.grant_role(person_id, ROLE_SUPERADMIN)
                session.flush()
            granted += 1
            log(f"GitHub id {github_id}: granted superadmin.")
        except IntegrityError:
            # A concurrent run granted it first; idempotent no-op.
            log(f"GitHub id {github_id}: already superadmin (concurrent); no change.")

    session.commit()
    return granted


def main(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    with _session_scope() as session:
        granted = bootstrap_admins(session, settings.superadmin_github_id_list)
    print(f"Bootstrap complete: {granted} grant(s) applied.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
