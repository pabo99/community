"""Seed registry and runner.

Each seed has a stable, unique ``seed_id`` and a callable that performs its
database operations against a Session (without committing). The runner:

- takes a transaction-level PostgreSQL advisory lock keyed on the seed id, so
  concurrent runners serialize and the same seed is never applied twice;
- checks the ``seed_executions`` table inside that locked transaction and skips
  if already recorded (re-run is a no-op);
- otherwise runs the seed's operations and inserts the ``seed_executions`` row,
  then commits — so the data and the record commit atomically. Any failure
  rolls back both, leaving the seed un-recorded and safe to retry.

A seed that has already executed is never re-run, so deleting seeded data (e.g.
a standard program) is not silently recreated on the next deployment.
"""

from __future__ import annotations

import zlib
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.engine import get_sessionmaker
from app.models.seed_execution import SeedExecution

# A fixed namespace so advisory-lock keys for seeds don't collide with other
# advisory-lock uses in the application.
_LOCK_NAMESPACE = 0x5EED


@dataclass(frozen=True)
class Seed:
    """A named, idempotent data seed."""

    seed_id: str
    run: Callable[[Session], None]


def _advisory_key(seed_id: str) -> int:
    """Deterministic 32-bit signed key for a seed id (for pg_advisory_xact_lock)."""
    unsigned = zlib.crc32(seed_id.encode("utf-8")) & 0xFFFFFFFF
    # Map to signed 32-bit range expected by the two-int advisory lock form.
    return unsigned - 0x100000000 if unsigned >= 0x80000000 else unsigned


def is_executed(session: Session, seed_id: str) -> bool:
    stmt = select(SeedExecution).where(SeedExecution.seed_id == seed_id)
    return session.scalars(stmt).one_or_none() is not None


def run_seed(session: Session, seed: Seed) -> bool:
    """Run a single seed atomically. Returns True if applied, False if skipped.

    Must be called with a session that is not mid-transaction in a way that
    conflicts; it commits on success.
    """
    # Serialize concurrent runners for this seed (released at transaction end).
    session.execute(
        text("SELECT pg_advisory_xact_lock(:ns, :key)"),
        {"ns": _LOCK_NAMESPACE, "key": _advisory_key(seed.seed_id)},
    )

    if is_executed(session, seed.seed_id):
        # Already applied by us or a concurrent runner that won the lock first.
        session.commit()
        return False

    try:
        seed.run(session)
        session.add(SeedExecution(seed_id=seed.seed_id))
        session.commit()
    except Exception:
        session.rollback()
        raise
    return True


def run_pending(session: Session, seeds: list[Seed]) -> dict[str, bool]:
    """Run all pending seeds in order. Returns {seed_id: applied?}."""
    results: dict[str, bool] = {}
    for seed in seeds:
        results[seed.seed_id] = run_seed(session, seed)
    return results


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
