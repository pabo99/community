"""Deterministic retry backoff.

A pure function mapping a (1-based) attempt number to the delay before the next
attempt becomes eligible. The schedule is deterministic (no jitter) so it is
trivially testable without a clock: ``delay = min(BASE * 2**(attempt-1), CAP)``.

No wall-clock sleeping happens here. Callers add the returned delay to a
reference ``now`` to compute a job's ``run_at``; eligibility is then driven by
``run_at <= now`` at claim time.

Jitter is intentionally omitted for V1 (single-tenant, low volume). It can be
added later without any schema or interface change.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Final

# First retry waits this long; each subsequent retry doubles, capped.
BACKOFF_BASE: Final = timedelta(seconds=10)
BACKOFF_CAP: Final = timedelta(seconds=300)


def backoff(attempt: int) -> timedelta:
    """Return the delay before the next attempt for a 1-based ``attempt``.

    ``attempt`` is the number of attempts already made (>= 1). The first retry
    (after attempt 1 failed) waits ``BACKOFF_BASE``; the delay doubles each
    time and is clamped to ``BACKOFF_CAP``.
    """
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    # Clamp the exponent to avoid overflow for large attempt counts; the cap
    # dominates well before this matters.
    exponent = min(attempt - 1, 32)
    seconds = BACKOFF_BASE.total_seconds() * (2**exponent)
    capped = min(seconds, BACKOFF_CAP.total_seconds())
    return timedelta(seconds=capped)
