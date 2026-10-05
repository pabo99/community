"""Shared test fixtures.

A dummy ``DATABASE_URL`` is set at collection time so unit tests can construct
the application and settings without a real database. ``/health/live`` and
config tests never open a connection. Integration tests (under
``tests/integration``) repoint this at the real test database and clear the
relevant caches.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

# Ensure required configuration exists for unit-level construction. Integration
# fixtures override DATABASE_URL with the real TEST_DATABASE_URL value.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/community_unit"
)

import pytest  # noqa: E402
from app.main import create_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Return a TestClient bound to a fresh application instance."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
