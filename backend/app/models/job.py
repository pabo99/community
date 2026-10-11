"""Persistent background job model.

A ``Job`` row is a unit of asynchronous work processed by the worker outside the
HTTP request path (technical-design.md §9). This module (M1-11a) defines only
the persistence shape; claiming, execution, retry, and recovery logic arrive in
later M1-11 commits.

Lifecycle (states only; transitions are implemented later):

    pending ──► running ──► succeeded
       ▲           │
       │           ├──► retrying ──► pending   (retriable failure, backoff)
       └───────────┘
                   └──► failed                 (terminal: attempts exhausted)

Design notes relevant to the schema (so later commits need no migration churn):

- **Claim ownership.** ``claim_token`` is a fresh UUID stamped on each claim
  attempt. Completion/failure transitions in M1-11b verify the token still
  matches before writing a result, so a worker whose lease expired (and whose
  job was requeued and re-claimed elsewhere) cannot overwrite the newer
  owner's outcome. ``locked_at``/``locked_by`` record the lease time and worker
  identity for recovery and observability.
- **Eligibility & backoff.** ``run_at`` is when the job becomes eligible to run.
  Retries set it into the future with a bounded backoff; this expresses delay
  declaratively (no wall-clock sleeps) and lets the claim query filter on
  ``run_at <= now()``.
- **At-least-once.** A crash between claim and completion leaves a stale
  ``running`` row that recovery requeues, so a handler may run more than once;
  handlers must be idempotent (documented with each handler in M1-11d).
- **Bounded, sanitized errors.** ``last_error`` stores a short, sanitized
  message only — never full tracebacks and never secrets. The column length is
  bounded and callers truncate to it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Final

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Job lifecycle states. ``retrying`` is a distinct, transient state (a failed
# attempt scheduled to run again) kept separate from ``pending`` for
# observability. Terminal states are ``succeeded`` and ``failed``.
STATUS_PENDING: Final = "pending"
STATUS_RUNNING: Final = "running"
STATUS_SUCCEEDED: Final = "succeeded"
STATUS_FAILED: Final = "failed"
STATUS_RETRYING: Final = "retrying"
JOB_STATUSES: Final = (
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
    STATUS_FAILED,
    STATUS_RETRYING,
)

# Default retry ceiling for a job (total attempts, including the first).
DEFAULT_MAX_ATTEMPTS: Final = 5

# Upper bound for the persisted, sanitized error message. Callers truncate to
# this; the column enforces it as a hard limit.
MAX_LAST_ERROR_LENGTH: Final = 2000

_STATUSES_SQL: Final = ", ".join(f"'{s}'" for s in JOB_STATUSES)


class Job(Base):
    """A persistent unit of asynchronous background work."""

    __tablename__ = "jobs"

    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUSES_SQL})", name="status_valid"),
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        CheckConstraint("max_attempts >= 1", name="max_attempts_positive"),
        CheckConstraint(
            f"last_error IS NULL OR length(last_error) <= {MAX_LAST_ERROR_LENGTH}",
            name="last_error_bounded",
        ),
        # Claim query: WHERE status IN (pending, retrying) AND run_at <= now()
        # ORDER BY run_at. A composite index keeps that selection cheap.
        Index("ix_jobs_status_run_at", "status", "run_at"),
        # Stale-lease recovery sweep scans running jobs by lease age.
        Index("ix_jobs_status_locked_at", "status", "locked_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Dispatch key into the handler registry (M1-11c).
    job_type: Mapped[str] = mapped_column(String(128))
    # Validated, bounded payload. Per-type Pydantic models validate it before
    # enqueue (M1-11b); the column itself defaults to an empty object.
    payload: Mapped[dict[str, object]] = mapped_column(
        JSONB, default=dict, server_default=func.text("'{}'")
    )

    status: Mapped[str] = mapped_column(String(32), default=STATUS_PENDING)

    # Attempt accounting. ``attempts`` increments on each claim; the job fails
    # terminally once a retriable failure occurs with attempts == max_attempts.
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default=func.text("0"))
    max_attempts: Mapped[int] = mapped_column(
        Integer, default=DEFAULT_MAX_ATTEMPTS, server_default=func.text(str(DEFAULT_MAX_ATTEMPTS))
    )

    # When the job becomes eligible to run (now for immediate work; future for
    # backed-off retries). Scheduling timestamp.
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Claim ownership (set when claimed, cleared on terminal/ requeue in later
    # commits). ``claim_token`` is unique per claim attempt; result writes
    # verify it to prevent a stale worker from clobbering a newer owner.
    claim_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), default=None)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    locked_by: Mapped[str | None] = mapped_column(String(128), default=None)

    # Execution timestamps.
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # Short, sanitized failure message (never a full traceback, never secrets).
    last_error: Mapped[str | None] = mapped_column(String(MAX_LAST_ERROR_LENGTH), default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # NOTE: `onupdate` is applied on ORM flush, not a database trigger.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
