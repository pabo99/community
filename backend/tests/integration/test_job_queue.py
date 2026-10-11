"""Integration tests for the JobQueue service against real PostgreSQL.

Single-connection tests: enqueue validation, claim eligibility, ownership-safe
completion/failure, retry backoff math, terminal failure, controlled error
recording (a secret in an exception is never persisted), and stale recovery.

The queue service commits; to keep tests isolated we bind the Session with
``join_transaction_mode="create_savepoint"`` so ``commit()`` only releases a
savepoint while the outer transaction is rolled back by the fixture (the same
pattern used by the seed-runner tests). Concurrency across separate real
connections is covered in ``test_job_queue_concurrency.py``.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from app.models.job import (
    STATUS_FAILED,
    STATUS_RETRYING,
    STATUS_RUNNING,
    STATUS_SUCCEEDED,
    Job,
)
from app.services.jobs import payloads
from app.services.jobs.backoff import backoff
from app.services.jobs.errors import (
    UNHANDLED_EXCEPTION_CODE,
    JobExecutionError,
    JobPayloadError,
    JobTypeError,
    error_code_for,
    format_last_error,
)
from app.services.jobs.queue import ClaimedJob, JobQueue
from sqlalchemy import Engine
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

# A registered type with no schema, used throughout. Registration is idempotent.
_TEST_TYPE = "test.noop"


@pytest.fixture(autouse=True)
def _register_type() -> None:
    payloads.register_job_type(_TEST_TYPE)


@pytest.fixture
def session(migrated_engine: Engine) -> Iterator[Session]:
    connection = migrated_engine.connect()
    transaction = connection.begin()
    sess = Session(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield sess
    finally:
        sess.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


def _now() -> datetime:
    return datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


# --- Enqueue -----------------------------------------------------------------


def test_enqueue_applies_defaults(session: Session) -> None:
    queue = JobQueue(session)
    job = queue.enqueue(_TEST_TYPE, {"k": "v"})
    assert job.status == "pending"
    assert job.attempts == 0
    assert job.payload == {"k": "v"}


def test_enqueue_rejects_unregistered_type(session: Session) -> None:
    queue = JobQueue(session)
    with pytest.raises(JobTypeError):
        queue.enqueue("totally.unknown", {})
    # Nothing persisted.
    assert session.query(Job).count() == 0


def test_enqueue_rejects_non_object_payload(session: Session) -> None:
    queue = JobQueue(session)
    with pytest.raises(JobPayloadError):
        queue.enqueue(_TEST_TYPE, ["not", "a", "dict"])  # type: ignore[arg-type]
    assert session.query(Job).count() == 0


def test_enqueue_rejects_oversize_payload(session: Session) -> None:
    queue = JobQueue(session)
    big = {"blob": "x" * (payloads.MAX_PAYLOAD_BYTES + 1)}
    with pytest.raises(JobPayloadError):
        queue.enqueue(_TEST_TYPE, big)
    assert session.query(Job).count() == 0


# --- Claim -------------------------------------------------------------------


def test_claim_marks_running_with_token(session: Session) -> None:
    queue = JobQueue(session)
    queue.enqueue(_TEST_TYPE, {}, run_at=_now())
    claimed = queue.claim("worker-1", now=_now())
    assert claimed is not None
    assert claimed.attempts == 1

    row = session.get(Job, claimed.id)
    assert row is not None
    assert row.status == STATUS_RUNNING
    assert row.claim_token == claimed.claim_token
    assert row.locked_by == "worker-1"
    assert row.locked_at == _now()
    assert row.started_at == _now()


def test_claim_returns_none_when_empty(session: Session) -> None:
    queue = JobQueue(session)
    assert queue.claim("worker-1", now=_now()) is None


def test_future_run_at_job_is_not_claimed(session: Session) -> None:
    queue = JobQueue(session)
    queue.enqueue(_TEST_TYPE, {}, run_at=_now() + timedelta(hours=1))
    assert queue.claim("worker-1", now=_now()) is None


# --- Ownership-safe transitions ----------------------------------------------


def test_complete_with_matching_token_succeeds(session: Session) -> None:
    queue = JobQueue(session)
    queue.enqueue(_TEST_TYPE, {}, run_at=_now())
    claimed = queue.claim("worker-1", now=_now())
    assert claimed is not None

    assert queue.complete(claimed.id, claimed.claim_token, now=_now()) is True
    row = session.get(Job, claimed.id)
    assert row is not None
    assert row.status == STATUS_SUCCEEDED
    assert row.finished_at == _now()
    assert row.claim_token is None
    assert row.locked_by is None


def test_complete_with_wrong_token_is_rejected(session: Session) -> None:
    queue = JobQueue(session)
    queue.enqueue(_TEST_TYPE, {}, run_at=_now())
    claimed = queue.claim("worker-1", now=_now())
    assert claimed is not None

    # A stale worker using a different token must not win.
    assert queue.complete(claimed.id, uuid.uuid4(), now=_now()) is False
    row = session.get(Job, claimed.id)
    assert row is not None
    assert row.status == STATUS_RUNNING  # unchanged


def test_fail_with_wrong_token_is_rejected(session: Session) -> None:
    queue = JobQueue(session)
    queue.enqueue(_TEST_TYPE, {}, run_at=_now())
    claimed = queue.claim("worker-1", now=_now())
    assert claimed is not None

    assert queue.fail(claimed.id, uuid.uuid4(), error_code="X", now=_now()) is False
    row = session.get(Job, claimed.id)
    assert row is not None
    assert row.status == STATUS_RUNNING


# --- Retry / backoff / terminal failure --------------------------------------


def test_fail_schedules_retry_with_backoff(session: Session) -> None:
    queue = JobQueue(session)
    queue.enqueue(_TEST_TYPE, {}, max_attempts=3, run_at=_now())
    claimed = queue.claim("worker-1", now=_now())
    assert claimed is not None  # attempts == 1

    assert queue.fail(claimed.id, claimed.claim_token, error_code="BOOM", now=_now()) is True
    row = session.get(Job, claimed.id)
    assert row is not None
    assert row.status == STATUS_RETRYING
    assert row.run_at == _now() + backoff(1)
    assert row.last_error == "BOOM"
    assert row.claim_token is None  # lease released


def test_fail_becomes_terminal_at_max_attempts(session: Session) -> None:
    queue = JobQueue(session)
    queue.enqueue(_TEST_TYPE, {}, max_attempts=1, run_at=_now())
    claimed = queue.claim("worker-1", now=_now())
    assert claimed is not None  # attempts == 1 == max_attempts

    assert queue.fail(claimed.id, claimed.claim_token, error_code="BOOM", now=_now()) is True
    row = session.get(Job, claimed.id)
    assert row is not None
    assert row.status == STATUS_FAILED
    assert row.finished_at == _now()


def test_attempts_never_exceed_max_attempts(session: Session) -> None:
    queue = JobQueue(session)
    queue.enqueue(_TEST_TYPE, {}, max_attempts=2, run_at=_now())

    # Attempt 1 -> retry.
    c1 = queue.claim("worker-1", now=_now())
    assert c1 is not None and c1.attempts == 1
    assert queue.fail(c1.id, c1.claim_token, error_code="E", now=_now()) is True

    # Make it eligible again and claim: attempt 2 -> terminal failure.
    later = _now() + backoff(1) + timedelta(seconds=1)
    c2 = queue.claim("worker-1", now=later)
    assert c2 is not None and c2.attempts == 2
    assert queue.fail(c2.id, c2.claim_token, error_code="E", now=later) is True

    row = session.get(Job, c2.id)
    assert row is not None
    assert row.status == STATUS_FAILED
    assert row.attempts == 2  # never exceeded max_attempts


# --- Controlled error recording (no secrets) ---------------------------------


def test_secret_in_exception_is_never_persisted(session: Session) -> None:
    secret = "SUPER_SECRET_TOKEN_abc123"
    # A handler failure whose underlying exception carries a secret. The queue
    # records only a controlled code; the detail must not leak the secret.
    code, detail = error_code_for(RuntimeError(f"db password is {secret}"))
    assert code == UNHANDLED_EXCEPTION_CODE
    assert detail is None

    queue = JobQueue(session)
    queue.enqueue(_TEST_TYPE, {}, max_attempts=1, run_at=_now())
    claimed = queue.claim("worker-1", now=_now())
    assert claimed is not None
    assert queue.fail(claimed.id, claimed.claim_token, error_code=code, detail=detail) is True

    row = session.get(Job, claimed.id)
    assert row is not None
    assert row.last_error is not None
    assert secret not in row.last_error
    assert row.last_error == UNHANDLED_EXCEPTION_CODE


def test_job_execution_error_detail_is_bounded_and_stripped(session: Session) -> None:
    # Even a controlled handler error has its detail sanitized/bounded.
    exc = JobExecutionError("VALIDATION_FAILED", detail="line1\nline2   with   spaces")
    code, detail = error_code_for(exc)
    stored = format_last_error(code, detail)
    assert "\n" not in stored
    assert stored.startswith("VALIDATION_FAILED: ")
    assert "line1 line2 with spaces" in stored


# --- Stale recovery ----------------------------------------------------------


def _claim_and_backdate(
    session: Session, queue: JobQueue, *, max_attempts: int, age_s: int
) -> ClaimedJob:
    queue.enqueue(_TEST_TYPE, {}, max_attempts=max_attempts, run_at=_now())
    claimed = queue.claim("worker-1", now=_now())
    assert claimed is not None
    # Back-date the lease so it looks expired relative to `now`.
    row = session.get(Job, claimed.id)
    assert row is not None
    row.locked_at = _now() - timedelta(seconds=age_s)
    session.flush()
    return claimed


def test_recover_stale_requeues_retriable(session: Session) -> None:
    queue = JobQueue(session)
    claimed = _claim_and_backdate(session, queue, max_attempts=3, age_s=600)

    recovered = queue.recover_stale(now=_now())
    assert recovered == 1
    row = session.get(Job, claimed.id)
    assert row is not None
    assert row.status == STATUS_RETRYING
    assert row.run_at == _now()  # immediately eligible
    assert row.claim_token is None  # token invalidated


def test_recover_stale_fails_exhausted(session: Session) -> None:
    queue = JobQueue(session)
    claimed = _claim_and_backdate(session, queue, max_attempts=1, age_s=600)

    recovered = queue.recover_stale(now=_now())
    assert recovered == 1
    row = session.get(Job, claimed.id)
    assert row is not None
    assert row.status == STATUS_FAILED  # respects max_attempts
    assert row.claim_token is None


def test_recover_stale_leaves_fresh_lease_untouched(session: Session) -> None:
    queue = JobQueue(session)
    queue.enqueue(_TEST_TYPE, {}, run_at=_now())
    claimed = queue.claim("worker-1", now=_now())
    assert claimed is not None

    # Lease is current (locked_at == now); nothing should be recovered.
    recovered = queue.recover_stale(now=_now())
    assert recovered == 0
    row = session.get(Job, claimed.id)
    assert row is not None
    assert row.status == STATUS_RUNNING
    assert row.claim_token == claimed.claim_token


def test_recovered_job_rejects_stale_worker_completion(session: Session) -> None:
    # The core safety property: after recovery nulls the token, the original
    # worker's late complete() must not succeed.
    queue = JobQueue(session)
    claimed = _claim_and_backdate(session, queue, max_attempts=3, age_s=600)
    assert queue.recover_stale(now=_now()) == 1

    assert queue.complete(claimed.id, claimed.claim_token, now=_now()) is False
    row = session.get(Job, claimed.id)
    assert row is not None
    assert row.status == STATUS_RETRYING  # not succeeded
