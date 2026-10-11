"""Unit tests for the deterministic retry backoff (no database, no clock)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from app.services.jobs.backoff import BACKOFF_BASE, BACKOFF_CAP, backoff


def test_first_retry_is_base() -> None:
    assert backoff(1) == BACKOFF_BASE


def test_exponential_until_cap() -> None:
    # 10s, 20s, 40s, 80s, 160s, then clamped at 300s.
    assert backoff(1) == timedelta(seconds=10)
    assert backoff(2) == timedelta(seconds=20)
    assert backoff(3) == timedelta(seconds=40)
    assert backoff(4) == timedelta(seconds=80)
    assert backoff(5) == timedelta(seconds=160)
    # 320s would exceed the cap, so it is clamped.
    assert backoff(6) == BACKOFF_CAP


def test_monotonic_non_decreasing() -> None:
    previous = timedelta(0)
    for attempt in range(1, 50):
        current = backoff(attempt)
        assert current >= previous
        previous = current


def test_never_exceeds_cap_for_large_attempts() -> None:
    # Must not overflow or exceed the cap even for very large attempt numbers.
    assert backoff(1000) == BACKOFF_CAP


def test_deterministic() -> None:
    assert backoff(3) == backoff(3)


def test_rejects_non_positive_attempt() -> None:
    with pytest.raises(ValueError):
        backoff(0)
