"""Job queue service: enqueue, claim, complete/fail, and stale recovery.

Owns transaction boundaries (the repository never commits). All timestamps are
timezone-aware UTC and ``now`` is injectable so behavior is deterministic in
tests without wall-clock sleeps.

Transaction model:

- **enqueue** — validate the payload, stage the row, commit. One transaction.
- **claim** — a short transaction: ``SELECT ... FOR UPDATE SKIP LOCKED`` the
  next eligible row, stamp it ``running`` with a FRESH ``claim_token`` and
  ``attempts += 1``, then COMMIT. The row lock is released at commit, BEFORE any
  handler runs, so a long handler never holds a lock. The method returns a
  detached :class:`ClaimedJob` snapshot, not a live ORM row, so the caller
  cannot accidentally mutate/commit the job mid-execution.
- **complete / fail** — a short transaction with an ownership-guarded UPDATE
  requiring BOTH ``status = running`` AND the matching ``claim_token``. A zero
  row count means ownership was lost (the lease expired and the job was
  recovered/re-claimed); the method returns ``False`` and writes nothing.
- **recover_stale** — one set-based transaction that requeues/fails expired
  leases and atomically nulls their ``claim_token``.

Failure classes are kept distinct: handler failures are recorded via controlled
error codes (:mod:`app.services.jobs.errors`); database/infrastructure
exceptions are NOT swallowed or written to a job — they propagate so the caller
(the future worker loop) can back off at the platform level.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Final

from sqlalchemy.orm import Session

from app.models.job import (
    DEFAULT_MAX_ATTEMPTS,
    STATUS_RUNNING,
    Job,
)
from app.repositories.job import JobRepository
from app.services.jobs.backoff import backoff
from app.services.jobs.errors import LEASE_EXPIRED_CODE, format_last_error
from app.services.jobs.payloads import validate_payload

# A lease older than this is considered expired by stale-job recovery. This is
# a timeout-based heuristic: it cannot distinguish a crashed worker from a slow
# but still-running one (see module/README notes), so it is set comfortably
# larger than any expected handler runtime. There is no heartbeat yet (M1-11b).
VISIBILITY_TIMEOUT: Final = timedelta(seconds=300)


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class ClaimedJob:
    """Immutable snapshot of a claimed job handed to the executor.

    Detached from the ORM session on purpose: the executor reads these fields
    and later calls ``complete``/``fail`` with ``id`` + ``claim_token``; it
    never holds a live row or an open transaction during handler execution.
    """

    id: uuid.UUID
    job_type: str
    payload: dict[str, object]
    attempts: int
    max_attempts: int
    claim_token: uuid.UUID


class JobQueue:
    """Concurrent-safe operations over the ``jobs`` table."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = JobRepository(session)

    # --- Enqueue -------------------------------------------------------------

    def enqueue(
        self,
        job_type: str,
        payload: Mapping[str, object] | None = None,
        *,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        run_at: datetime | None = None,
    ) -> Job:
        """Validate and persist a new job. Commits. Returns the stored Job.

        Raises ``JobTypeError``/``JobPayloadError`` BEFORE touching the database
        if the type is unregistered or the payload is invalid/oversize.
        """
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        normalized = validate_payload(job_type, payload or {})
        job = Job(
            job_type=job_type,
            payload=normalized,
            max_attempts=max_attempts,
            run_at=run_at or _utcnow(),
        )
        self._repo.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    # --- Claim ---------------------------------------------------------------

    def claim(self, worker_id: str, *, now: datetime | None = None) -> ClaimedJob | None:
        """Atomically claim the next eligible job, or return None.

        Commits the claim before returning so the row lock is released and the
        caller can execute the handler without holding a transaction. Each claim
        gets a fresh ``claim_token``.
        """
        reference = now or _utcnow()
        job = self._repo.select_claimable(reference)
        if job is None:
            # Nothing eligible: end the (empty) transaction cleanly.
            self._session.commit()
            return None

        token = uuid.uuid4()
        job.status = STATUS_RUNNING
        job.attempts += 1
        job.claim_token = token
        job.locked_by = worker_id
        job.locked_at = reference
        job.started_at = reference
        job.finished_at = None
        job.last_error = None
        self._session.flush()

        snapshot = ClaimedJob(
            id=job.id,
            job_type=job.job_type,
            payload=dict(job.payload),
            attempts=job.attempts,
            max_attempts=job.max_attempts,
            claim_token=token,
        )
        self._session.commit()
        return snapshot

    # --- Ownership-safe result transitions -----------------------------------

    def complete(
        self, job_id: uuid.UUID, claim_token: uuid.UUID, *, now: datetime | None = None
    ) -> bool:
        """Mark a job succeeded if still owned. True on success, False if ownership lost."""
        reference = now or _utcnow()
        updated = self._repo.mark_succeeded(job_id, claim_token, reference)
        self._session.commit()
        return updated == 1

    def fail(
        self,
        job_id: uuid.UUID,
        claim_token: uuid.UUID,
        *,
        error_code: str,
        detail: str | None = None,
        now: datetime | None = None,
    ) -> bool:
        """Record a handler failure if still owned.

        Retries with backoff while ``attempts < max_attempts``; otherwise marks
        the job terminally ``failed``. Returns True if the transition was
        applied, False if ownership was lost (a stale worker). The decision uses
        the row's own ``attempts``/``max_attempts`` read inside this transaction
        so the attempt count can never exceed ``max_attempts``.

        ``error_code`` (+ optional ``detail``) are recorded via the controlled,
        bounded ``last_error`` formatter — never a raw exception string.
        """
        reference = now or _utcnow()
        job = self._repo.get(job_id)
        # Verify ownership against the freshly-read row BEFORE deciding. If the
        # row is no longer running under this token, ownership is lost.
        if job is None or job.status != STATUS_RUNNING or job.claim_token != claim_token:
            self._session.commit()
            return False

        last_error = format_last_error(error_code, detail)
        if job.attempts < job.max_attempts:
            run_at = reference + backoff(job.attempts)
            updated = self._repo.mark_retrying(
                job_id, claim_token, run_at=run_at, last_error=last_error
            )
        else:
            updated = self._repo.mark_failed(
                job_id, claim_token, now=reference, last_error=last_error
            )
        self._session.commit()
        return updated == 1

    # --- Stale-job recovery --------------------------------------------------

    def recover_stale(
        self,
        *,
        now: datetime | None = None,
        visibility_timeout: timedelta = VISIBILITY_TIMEOUT,
    ) -> int:
        """Requeue/fail jobs whose lease expired; invalidate their claim token.

        Returns the number of jobs recovered. Retriable stale jobs become
        ``retrying`` and immediately eligible; exhausted ones become ``failed``.
        ``claim_token`` is nulled atomically so the previous owner's late
        completion/failure can no longer match.

        LIMITATION: this is a timeout heuristic. An expired lease does NOT prove
        the worker crashed — a slow-but-alive worker can be recovered and its
        job re-run elsewhere (at-least-once). Handlers must be idempotent. A
        heartbeat/lease-renewal scheme would narrow the window and is a future
        enhancement (intentionally not built here).
        """
        reference = now or _utcnow()
        cutoff = reference - visibility_timeout
        recovered = self._repo.recover_stale(
            cutoff=cutoff,
            now=reference,
            last_error=format_last_error(LEASE_EXPIRED_CODE),
        )
        self._session.commit()
        return recovered
