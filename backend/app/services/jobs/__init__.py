"""Job queue service package.

Concurrent, PostgreSQL-backed job queue operations (M1-11b): enqueue, atomic
claim with ``FOR UPDATE SKIP LOCKED``, ownership-safe completion/failure,
deterministic retry backoff, and stale-job recovery. No worker process or
scheduler lives here (M1-11c/M1-12); this package provides the primitives a
worker will drive.
"""
