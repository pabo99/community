"""Migration integration tests against a real, empty PostgreSQL database.

These verify that ``alembic upgrade head`` builds the schema from an empty
database (never ``Base.metadata.create_all``) and reaches the expected baseline
head, creating only Alembic's own bookkeeping table at M1-03.
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

# Dedicated throwaway database for the empty-database migration test, kept
# distinct from the shared migrated test database.
_EMPTY_DB_NAME = "community_migration_check"


def _server_url(test_database_url: str) -> str:
    """Return a URL to the maintenance 'postgres' database on the same server."""
    parts = urlsplit(test_database_url)
    return test_database_url.replace(parts.path, "/postgres")


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
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", empty_database_url)

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
            # The baseline creates only Alembic's bookkeeping table.
            assert tables == {"alembic_version"}

            # The applied revision is the expected baseline head.
            script = ScriptDirectory.from_config(config)
            expected_head = script.get_current_head()
            applied = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert applied == expected_head
    finally:
        engine.dispose()
