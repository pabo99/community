"""Persistence for background jobs.

Data-access primitives for the job queue: staging an enqueue, the atomic claim
SELECT (``FOR UPDATE SKIP LOCKED``), ownership-guarded result UPDATEs, and the
stale-job recovery sweep. Consistent with the project convention, the
repository never commits — the service owns the transaction boundary. The
guarded UPDATEs return the affected row count so the service can detect lost
ownership.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, cast

from sqlalchemy import CursorResult, case, select, update
from sqlalchemy.orm import Session
from sqlalchemy.sql.dml import Update

from app.models.job import (
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RETRYING,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
    Job,
)


class JobRepository:
    """Data access for the ``jobs`` table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _execute_rowcount(self, stmt: Update) -> int:
        """Execute a DML UPDATE and return the affected row count."""
        result = cast("CursorResult[Any]", self._session.execute(stmt))
        return result.rowcount

    # --- Enqueue -------------------------------------------------------------

    def add(self, job: Job) -> Job:
        """Stage a new job. The caller commits."""
        self._session.add(job)
        return job

    def get(self, job_id: uuid.UUID) -> Job | None:
        return self._session.get(Job, job_id)

    # --- Claim ---------------------------------------------------------------

    def select_claimable(self, now: datetime) -> Job | None:
        """Lock and return the next eligible job, or None.

        Uses ``FOR UPDATE SKIP LOCKED`` so concurrent claimers never block on or
        double-claim the same row: a row another transaction has locked is
        skipped, and the next eligible row is returned instead. Eligibility is
        ``status IN (pending, retrying) AND run_at <= now``. The row lock is
        held until the caller's transaction ends.
        """
        stmt = (
            select(Job)
            .where(
                Job.status.in_((STATUS_PENDING, STATUS_RETRYING)),
                Job.run_at <= now,
            )
            .order_by(Job.run_at, Job.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return self._session.scalars(stmt).one_or_none()

    # --- Ownership-guarded result transitions --------------------------------

    def mark_succeeded(self, job_id: uuid.UUID, claim_token: uuid.UUID, now: datetime) -> int:
        """Mark a job succeeded iff it is still running under ``claim_token``.

        Returns the number of rows updated (1 on success, 0 if ownership was
        lost). The guard requires BOTH ``status = running`` AND the matching
        ``claim_token`` so a stale worker cannot overwrite a newer attempt.
        """
        stmt = (
            update(Job)
            .where(
                Job.id == job_id,
                Job.status == STATUS_RUNNING,
                Job.claim_token == claim_token,
            )
            .values(
                status=STATUS_SUCCEEDED,
                finished_at=now,
                last_error=None,
                claim_token=None,
                locked_at=None,
                locked_by=None,
            )
        )
        return self._execute_rowcount(stmt)

    def mark_retrying(
        self,
        job_id: uuid.UUID,
        claim_token: uuid.UUID,
        *,
        run_at: datetime,
        last_error: str,
    ) -> int:
        """Schedule a retry iff still running under ``claim_token``. Returns rowcount."""
        stmt = (
            update(Job)
            .where(
                Job.id == job_id,
                Job.status == STATUS_RUNNING,
                Job.claim_token == claim_token,
            )
            .values(
                status=STATUS_RETRYING,
                run_at=run_at,
                last_error=last_error,
                claim_token=None,
                locked_at=None,
                locked_by=None,
                finished_at=None,
            )
        )
        return self._execute_rowcount(stmt)

    def mark_failed(
        self,
        job_id: uuid.UUID,
        claim_token: uuid.UUID,
        *,
        now: datetime,
        last_error: str,
    ) -> int:
        """Mark a job terminally failed iff still running under ``claim_token``.

        Returns rowcount (1 success, 0 ownership lost).
        """
        stmt = (
            update(Job)
            .where(
                Job.id == job_id,
                Job.status == STATUS_RUNNING,
                Job.claim_token == claim_token,
            )
            .values(
                status=STATUS_FAILED,
                finished_at=now,
                last_error=last_error,
                claim_token=None,
                locked_at=None,
                locked_by=None,
            )
        )
        return self._execute_rowcount(stmt)

    # --- Stale-job recovery --------------------------------------------------

    def recover_stale(self, *, cutoff: datetime, now: datetime, last_error: str) -> int:
        """Requeue or fail jobs whose lease expired. Returns rows recovered.

        A job is stale when ``status = running`` and ``locked_at <= cutoff``.
        Retriable stale jobs (``attempts < max_attempts``) go back to
        ``retrying`` and become immediately eligible (``run_at = now``);
        exhausted ones go to ``failed``. In BOTH cases ``claim_token`` is
        atomically set to NULL in the same statement, so the previous owner's
        ownership-guarded completion/failure can no longer match — a stale
        worker that returns late is harmless.
        """
        stmt = (
            update(Job)
            .where(Job.status == STATUS_RUNNING, Job.locked_at <= cutoff)
            .values(
                status=case(
                    (Job.attempts < Job.max_attempts, STATUS_RETRYING),
                    else_=STATUS_FAILED,
                ),
                run_at=case((Job.attempts < Job.max_attempts, now), else_=Job.run_at),
                finished_at=case((Job.attempts < Job.max_attempts, None), else_=now),
                last_error=last_error,
                claim_token=None,
                locked_at=None,
                locked_by=None,
            )
        )
        return self._execute_rowcount(stmt)
