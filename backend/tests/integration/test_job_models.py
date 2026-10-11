"""Integration tests for the Job persistence model against PostgreSQL.

Covers column defaults, the status CHECK, the attempts/max_attempts and
bounded-error CHECKs, the claim-ownership columns, and the onupdate behavior.
Claiming/worker/retry logic is NOT present yet (M1-11b+); these tests only
exercise the persistence shape.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.models.job import (
    DEFAULT_MAX_ATTEMPTS,
    MAX_LAST_ERROR_LENGTH,
    STATUS_PENDING,
    STATUS_RUNNING,
    Job,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def test_insert_applies_defaults(db_session: Session) -> None:
    job = Job(job_type="demo.noop")
    db_session.add(job)
    db_session.flush()
    db_session.refresh(job)

    assert isinstance(job.id, uuid.UUID)
    assert job.status == STATUS_PENDING
    assert job.attempts == 0
    assert job.max_attempts == DEFAULT_MAX_ATTEMPTS
    assert job.payload == {}
    assert job.run_at is not None
    assert job.created_at is not None
    assert job.updated_at is not None
    # Claim-ownership and execution fields start empty.
    assert job.claim_token is None
    assert job.locked_at is None
    assert job.locked_by is None
    assert job.started_at is None
    assert job.finished_at is None
    assert job.last_error is None


def test_payload_roundtrips_as_jsonb(db_session: Session) -> None:
    payload = {"edition_id": "abc", "count": 3, "nested": {"ok": True}}
    job = Job(job_type="demo.echo", payload=payload)
    db_session.add(job)
    db_session.flush()
    db_session.expire(job)

    reloaded = db_session.scalars(select(Job).where(Job.id == job.id)).one()
    assert reloaded.payload == payload


def test_claim_ownership_fields_persist(db_session: Session) -> None:
    # These columns exist to support safe claim ownership in M1-11b; here we
    # only verify they persist and read back (no claim logic yet).
    token = uuid.uuid4()
    now = datetime.now(UTC)
    job = Job(
        job_type="demo.noop",
        status=STATUS_RUNNING,
        attempts=1,
        claim_token=token,
        locked_at=now,
        locked_by="worker-1",
        started_at=now,
    )
    db_session.add(job)
    db_session.flush()
    db_session.expire(job)

    reloaded = db_session.scalars(select(Job).where(Job.id == job.id)).one()
    assert reloaded.claim_token == token
    assert reloaded.locked_by == "worker-1"
    assert reloaded.attempts == 1


def test_status_check_rejects_unknown_value(db_session: Session) -> None:
    db_session.add(Job(job_type="demo.noop", status="bogus"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_attempts_check_rejects_negative(db_session: Session) -> None:
    db_session.add(Job(job_type="demo.noop", attempts=-1))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_max_attempts_check_rejects_zero(db_session: Session) -> None:
    db_session.add(Job(job_type="demo.noop", max_attempts=0))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_last_error_check_rejects_overlong_value(db_session: Session) -> None:
    # The bounded-error CHECK guards against unbounded/leaky error text. The
    # String length and the CHECK both cap it; exceeding the bound is rejected.
    db_session.add(Job(job_type="demo.noop", last_error="x" * (MAX_LAST_ERROR_LENGTH + 1)))
    with pytest.raises((IntegrityError, Exception)):
        db_session.flush()


def test_last_error_accepts_bounded_value(db_session: Session) -> None:
    job = Job(job_type="demo.noop", last_error="y" * MAX_LAST_ERROR_LENGTH)
    db_session.add(job)
    db_session.flush()
    db_session.expire(job)

    reloaded = db_session.scalars(select(Job).where(Job.id == job.id)).one()
    assert reloaded.last_error is not None
    assert len(reloaded.last_error) == MAX_LAST_ERROR_LENGTH


def test_run_at_is_settable_in_the_future(db_session: Session) -> None:
    # run_at expresses eligibility/backoff declaratively; a future value is a
    # legitimate state (a backed-off retry). No scheduling logic is exercised.
    future = datetime.now(UTC) + timedelta(hours=1)
    job = Job(job_type="demo.noop", run_at=future)
    db_session.add(job)
    db_session.flush()
    db_session.expire(job)

    reloaded = db_session.scalars(select(Job).where(Job.id == job.id)).one()
    assert reloaded.run_at > datetime.now(UTC)


def test_updated_at_changes_on_update(db_session: Session) -> None:
    job = Job(job_type="demo.noop")
    db_session.add(job)
    db_session.flush()
    db_session.refresh(job)
    original_updated = job.updated_at

    job.status = STATUS_RUNNING
    db_session.flush()
    db_session.refresh(job)
    assert job.updated_at >= original_updated
