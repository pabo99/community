"""Fixtures for real-PostgreSQL integration tests.

Integration tests run against a dedicated TEST database on the same PostgreSQL
service as development. They never use SQLite and never fall back to the
development database:

- ``TEST_DATABASE_URL`` must be set explicitly.
- If it resolves to the same database as ``DATABASE_URL``, the tests refuse to
  run (defensive guard), so a misconfiguration can never mutate dev data.

Schema is established by running Alembic ``upgrade head`` once per test session.
Per-test isolation uses an outer transaction that is rolled back after each
test, so no committed state leaks between tests.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from urllib.parse import urlsplit

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


def _database_identity(url: str) -> tuple[str, str, str, str]:
    """Return (host, port, path, query) identifying the target database.

    Credentials are intentionally excluded; two URLs that differ only by
    username/password but point at the same host+database are the same target.
    """
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    port = str(parts.port or 5432)
    return (host, port, parts.path, parts.query)


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Resolve and validate the integration-test database URL."""
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        pytest.fail(
            "TEST_DATABASE_URL is not set. Integration tests require an explicit "
            "test database and never fall back to DATABASE_URL."
        )

    dev_url = os.environ.get("DATABASE_URL")
    if dev_url and _database_identity(test_url) == _database_identity(dev_url):
        pytest.fail(
            "TEST_DATABASE_URL resolves to the same database as DATABASE_URL. "
            "Integration tests require a separate test database."
        )

    return test_url


@pytest.fixture(scope="session")
def alembic_config(test_database_url: str) -> Config:
    """Alembic config pointed at the test database."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", test_database_url)
    return config


@pytest.fixture(scope="session")
def migrated_engine(test_database_url: str, alembic_config: Config) -> Iterator[Engine]:
    """Engine against the test DB with the schema migrated to head.

    The schema is built by Alembic migrations (never ``create_all``).
    """
    engine = create_engine(test_database_url, pool_pre_ping=True, future=True)
    # Point the application engine at the test database for code under test.
    os.environ["DATABASE_URL"] = test_database_url

    command.upgrade(alembic_config, "head")
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(migrated_engine: Engine) -> Iterator[Session]:
    """Provide a Session wrapped in a transaction that is rolled back.

    Each test runs inside an outer transaction on a dedicated connection;
    rolling back after the test discards any changes, keeping tests isolated
    without rebuilding the schema per test.
    """
    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
