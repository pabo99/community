"""Concurrency tests for the JobQueue over REAL overlapping PostgreSQL transactions.

Unlike the single-connection tests, these use multiple independent connections
with their own transactions so they exercise genuine ``FOR UPDATE SKIP LOCKED``
behavior, lease loss, and recovery races. They commit real rows and clean them
up explicitly at the end.

Determinism without wall-clock sleeps:
- Overlap is created by holding one transaction open while another acts, not by
  sleeping. The "held" transaction has already locked its row before the other
  connection runs, so ordering is deterministic.
- Each worker connection sets a bounded ``lock_timeout`` and
  ``statement_timeout`` so that if a claim ever BLOCKED (it must not, thanks to
  SKIP LOCKED), the test fails fast with an error instead of hanging.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from app.models.job import STATUS_RETRYING, STATUS_SUCCEEDED, Job
from app.services.jobs import payloads
from app.services.jobs.queue import JobQueue
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

_TEST_TYPE = "test.concurrency"
# Bounded timeouts (ms): a claim must never wait on a locked row (SKIP LOCKED),
# so these only ever trip if something is wrong — turning a hang into a failure.
_LOCK_TIMEOUT_MS = 2000
_STATEMENT_TIMEOUT_MS = 5000


@pytest.fixture(autouse=True)
def _register_type() -> None:
    payloads.register_job_type(_TEST_TYPE)


def _bounded_session(engine: Engine) -> Session:
    """A committing Session on its own connection with bounded lock timeouts."""
    connection = engine.connect()
    connection.execute(text(f"SET lock_timeout = {_LOCK_TIMEOUT_MS}"))
    connection.execute(text(f"SET statement_timeout = {_STATEMENT_TIMEOUT_MS}"))
    connection.commit()
    return Session(bind=connection, expire_on_commit=False)


@pytest.fixture
def cleanup(migrated_engine: Engine) -> Iterator[None]:
    """Delete any jobs this module's tests committed, afterwards."""
    yield
    cleaner = Session(bind=migrated_engine.connect(), expire_on_commit=False)
    try:
        for job in cleaner.scalars(select(Job).where(Job.job_type == _TEST_TYPE)).all():
            cleaner.delete(job)
        cleaner.commit()
    finally:
        cleaner.close()


def test_held_lock_is_skipped_not_waited_on(migrated_engine: Engine, cleanup: None) -> None:
    """Hold a row lock open in A; B must SKIP the locked row (not block/claim it)."""
    # Enqueue exactly one eligible job (committed so other connections see it).
    producer = _bounded_session(migrated_engine)
    try:
        job = JobQueue(producer).enqueue(_TEST_TYPE, {})
        job_id = job.id
    finally:
        producer.close()

    # Connection A: lock the row with FOR UPDATE SKIP LOCKED and HOLD the
    # transaction open (do not commit yet).
    conn_a = migrated_engine.connect()
    try:
        locked = conn_a.execute(
            text("SELECT id FROM jobs WHERE id = :id FOR UPDATE SKIP LOCKED"),
            {"id": job_id},
        ).scalar_one_or_none()
        assert locked == job_id  # A holds the lock now (transaction still open)

        # Connection B: attempt to claim. With SKIP LOCKED it must immediately
        # skip A's locked row and find nothing else -> None, WITHOUT waiting.
        session_b = _bounded_session(migrated_engine)
        try:
            claimed = JobQueue(session_b).claim("worker-B")
            assert claimed is None  # skipped the locked row, did not block
        finally:
            session_b.close()
    finally:
        conn_a.rollback()  # release A's lock
        conn_a.close()

    # After A releases, the row is claimable again.
    session_c = _bounded_session(migrated_engine)
    try:
        claimed = JobQueue(session_c).claim("worker-C")
        assert claimed is not None
        assert claimed.id == job_id
    finally:
        session_c.close()


def test_two_workers_cannot_claim_the_same_job(migrated_engine: Engine, cleanup: None) -> None:
    """Two eligible jobs, two workers: each gets a DISTINCT job; a third gets None."""
    producer = _bounded_session(migrated_engine)
    try:
        q = JobQueue(producer)
        q.enqueue(_TEST_TYPE, {})
        q.enqueue(_TEST_TYPE, {})
    finally:
        producer.close()

    session_a = _bounded_session(migrated_engine)
    session_b = _bounded_session(migrated_engine)
    session_c = _bounded_session(migrated_engine)
    try:
        claimed_a = JobQueue(session_a).claim("worker-A")
        claimed_b = JobQueue(session_b).claim("worker-B")
        claimed_c = JobQueue(session_c).claim("worker-C")

        assert claimed_a is not None
        assert claimed_b is not None
        assert claimed_a.id != claimed_b.id  # never the same row
        assert claimed_c is None  # only two jobs existed
    finally:
        session_a.close()
        session_b.close()
        session_c.close()


def test_stale_worker_cannot_complete_after_recovery(
    migrated_engine: Engine, cleanup: None
) -> None:
    """A loses its lease; B claims; A's late complete() loses to B's token."""
    producer = _bounded_session(migrated_engine)
    try:
        job = JobQueue(producer).enqueue(_TEST_TYPE, {}, max_attempts=3)
        job_id = job.id
    finally:
        producer.close()

    # Worker A claims (token T_A).
    session_a = _bounded_session(migrated_engine)
    # Worker B operates on its own connection.
    session_b = _bounded_session(migrated_engine)
    try:
        queue_a = JobQueue(session_a)
        claimed_a = queue_a.claim("worker-A")
        assert claimed_a is not None

        # Force the lease to look expired (back-date locked_at) via B's conn,
        # then recover: this nulls A's token and requeues the job.
        session_b.execute(
            text("UPDATE jobs SET locked_at = now() - interval '1 hour' WHERE id = :id"),
            {"id": job_id},
        )
        session_b.commit()
        assert JobQueue(session_b).recover_stale() == 1

        # Worker B claims the requeued job (token T_B != T_A).
        claimed_b = JobQueue(session_b).claim("worker-B")
        assert claimed_b is not None
        assert claimed_b.claim_token != claimed_a.claim_token

        # A returns late and tries to complete with its stale token -> rejected.
        assert queue_a.complete(claimed_a.id, claimed_a.claim_token) is False
        # B completes successfully with its current token.
        assert JobQueue(session_b).complete(claimed_b.id, claimed_b.claim_token) is True

        session_a.expire_all()
        row = session_a.get(Job, job_id)
        assert row is not None
        assert row.status == STATUS_SUCCEEDED
        assert row.locked_by == "worker-B" or row.locked_by is None
    finally:
        session_a.close()
        session_b.close()


def test_concurrent_recovery_does_not_corrupt(migrated_engine: Engine, cleanup: None) -> None:
    """Two overlapping recovery transactions must not double-recover one job."""
    producer = _bounded_session(migrated_engine)
    try:
        job = JobQueue(producer).enqueue(_TEST_TYPE, {}, max_attempts=3)
        job_id = job.id
    finally:
        producer.close()

    # Claim then expire the lease.
    claimer = _bounded_session(migrated_engine)
    try:
        JobQueue(claimer).claim("worker-A")
    finally:
        claimer.close()
    expirer = _bounded_session(migrated_engine)
    try:
        expirer.execute(
            text("UPDATE jobs SET locked_at = now() - interval '1 hour' WHERE id = :id"),
            {"id": job_id},
        )
        expirer.commit()
    finally:
        expirer.close()

    # Two recovery operations run on separate connections. The row-level locks
    # taken by the UPDATE serialize them: exactly one observes status='running'
    # and recovers; the other sees it already requeued and recovers nothing.
    session_a = _bounded_session(migrated_engine)
    session_b = _bounded_session(migrated_engine)
    try:
        recovered_a = JobQueue(session_a).recover_stale()
        recovered_b = JobQueue(session_b).recover_stale()
        assert recovered_a + recovered_b == 1  # recovered exactly once
    finally:
        session_a.close()
        session_b.close()

    verifier = _bounded_session(migrated_engine)
    try:
        row = verifier.get(Job, job_id)
        assert row is not None
        assert row.status == STATUS_RETRYING
        assert row.attempts == 1  # not double-incremented
        assert row.claim_token is None
    finally:
        verifier.close()


def test_one_job_failure_does_not_corrupt_others(migrated_engine: Engine, cleanup: None) -> None:
    """Failing one job leaves an unrelated job completely unaffected."""
    producer = _bounded_session(migrated_engine)
    try:
        q = JobQueue(producer)
        job_fail = q.enqueue(_TEST_TYPE, {"which": "fail"}, max_attempts=1)
        job_ok = q.enqueue(_TEST_TYPE, {"which": "ok"}, max_attempts=1)
        fail_id, ok_id = job_fail.id, job_ok.id
    finally:
        producer.close()

    worker = _bounded_session(migrated_engine)
    try:
        queue = JobQueue(worker)
        # Claim both (two separate claim transactions).
        first = queue.claim("worker-1")
        second = queue.claim("worker-1")
        assert first is not None and second is not None
        by_id = {first.id: first, second.id: second}

        # Fail one, complete the other.
        assert queue.fail(by_id[fail_id].id, by_id[fail_id].claim_token, error_code="BOOM") is True
        assert queue.complete(by_id[ok_id].id, by_id[ok_id].claim_token) is True
    finally:
        worker.close()

    verifier = _bounded_session(migrated_engine)
    try:
        failed = verifier.get(Job, fail_id)
        ok = verifier.get(Job, ok_id)
        assert failed is not None and failed.status == "failed"
        assert ok is not None and ok.status == STATUS_SUCCEEDED
        assert ok.last_error is None  # the failure did not bleed into the other job
    finally:
        verifier.close()


def test_claim_does_not_block_on_running_job(migrated_engine: Engine, cleanup: None) -> None:
    """A job already running (claimed) is not re-selected; claim returns None fast."""
    producer = _bounded_session(migrated_engine)
    try:
        JobQueue(producer).enqueue(_TEST_TYPE, {})
    finally:
        producer.close()

    session_a = _bounded_session(migrated_engine)
    session_b = _bounded_session(migrated_engine)
    try:
        claimed_a = JobQueue(session_a).claim("worker-A")
        assert claimed_a is not None
        # The job is now 'running'; B must not claim it and must not block.
        claimed_b = JobQueue(session_b).claim("worker-B")
        assert claimed_b is None
        # Sanity: distinct token identity would be impossible since B got nothing.
        assert isinstance(claimed_a.claim_token, uuid.UUID)
        assert session_b.get(Job, claimed_a.id) is not None
    finally:
        session_a.close()
        session_b.close()
