"""Migration integration tests against a real, empty PostgreSQL database.

These verify that ``alembic upgrade head`` builds the schema from an empty
database (never ``Base.metadata.create_all``) and reaches the expected head,
and that upgrade/downgrade of the identity revision round-trips cleanly.
"""

from __future__ import annotations

from collections.abc import Iterator
from urllib.parse import urlsplit

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import NullPool

pytestmark = pytest.mark.integration

# Dedicated throwaway database for migration tests, kept distinct from the
# shared migrated test database.
_EMPTY_DB_NAME = "community_migration_check"

# Baseline (M1-03), identity (M1-05), and sessions (M1-06) revisions.
_BASELINE_REVISION = "e049e161a164"
_IDENTITY_REVISION = "0b92c4c6d996"
_SESSIONS_REVISION = "8f8deb9d2cd7"

# Tables introduced by the identity revision.
_IDENTITY_TABLES = {"persons", "external_identities"}
# Tables introduced by the sessions revision.
_SESSION_TABLES = {"user_sessions", "oauth_states"}


def _server_url(test_database_url: str) -> str:
    """Return a URL to the maintenance 'postgres' database on the same server."""
    parts = urlsplit(test_database_url)
    return test_database_url.replace(parts.path, "/postgres")


def _alembic_config(url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    return config


@pytest.fixture
def empty_database_url(test_database_url: str) -> Iterator[str]:
    """Create a fresh empty database and drop it afterwards."""
    server_url = _server_url(test_database_url)
    admin = create_engine(server_url, isolation_level="AUTOCOMMIT", future=True)
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{_EMPTY_DB_NAME}"'))
        conn.execute(text(f'CREATE DATABASE "{_EMPTY_DB_NAME}"'))

    empty_url = test_database_url.replace(urlsplit(test_database_url).path, f"/{_EMPTY_DB_NAME}")
    try:
        yield empty_url
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{_EMPTY_DB_NAME}"'))
        admin.dispose()


def test_upgrade_head_from_empty_database(empty_database_url: str) -> None:
    config = _alembic_config(empty_database_url)

    # Starting point: an empty database with no tables at all. NullPool ensures
    # each connection sees the latest catalog after the migration commits.
    engine = create_engine(empty_database_url, future=True, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            assert inspect(conn).get_table_names() == []

        command.upgrade(config, "head")

        # Inspect on a fresh connection so the catalog reflects the migration.
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            # Head creates identity + session tables plus Alembic's bookkeeping.
            assert _IDENTITY_TABLES.issubset(tables)
            assert _SESSION_TABLES.issubset(tables)
            assert "alembic_version" in tables

            # The applied revision is the current head.
            script = ScriptDirectory.from_config(config)
            expected_head = script.get_current_head()
            applied = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert applied == expected_head
        assert expected_head == _SESSIONS_REVISION
    finally:
        engine.dispose()


def test_identity_revision_upgrade_downgrade_roundtrip(empty_database_url: str) -> None:
    config = _alembic_config(empty_database_url)
    engine = create_engine(empty_database_url, future=True, poolclass=NullPool)
    try:
        # Upgrade to the identity revision: identity tables exist.
        command.upgrade(config, _IDENTITY_REVISION)
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
        assert _IDENTITY_TABLES.issubset(tables)

        # Downgrade one step: identity tables are dropped, baseline remains.
        command.downgrade(config, _BASELINE_REVISION)
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            applied = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert not (_IDENTITY_TABLES & tables)
        assert applied == _BASELINE_REVISION
    finally:
        engine.dispose()


def test_sessions_revision_upgrade_downgrade_roundtrip(empty_database_url: str) -> None:
    config = _alembic_config(empty_database_url)
    engine = create_engine(empty_database_url, future=True, poolclass=NullPool)
    try:
        # Upgrade to the sessions revision: session tables exist.
        command.upgrade(config, _SESSIONS_REVISION)
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
        assert _SESSION_TABLES.issubset(tables)

        # Downgrade one step: session tables dropped, identity tables remain.
        command.downgrade(config, _IDENTITY_REVISION)
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            applied = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert not (_SESSION_TABLES & tables)
        assert _IDENTITY_TABLES.issubset(tables)
        assert applied == _IDENTITY_REVISION
    finally:
        engine.dispose()
