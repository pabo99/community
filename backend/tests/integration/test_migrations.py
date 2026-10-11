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

# Revisions: baseline (M1-03), identity (M1-05), sessions (M1-06), roles
# (M1-07), program/edition/project (M1-08), simplify-domain (M1-10 redesign).
_BASELINE_REVISION = "e049e161a164"
_IDENTITY_REVISION = "0b92c4c6d996"
_SESSIONS_REVISION = "8f8deb9d2cd7"
_ROLES_REVISION = "7c57bafdf5d6"
_PROGRAM_REVISION = "1fa4c82c5a08"
_SIMPLIFY_REVISION = "2c7f1e9b4a30"
_SEED_EXEC_REVISION = "3d8b2f6c1a52"

# Tables introduced by the identity revision.
_IDENTITY_TABLES = {"persons", "external_identities"}
# Tables introduced by the sessions revision.
_SESSION_TABLES = {"user_sessions", "oauth_states"}
# Tables introduced by the roles revision.
_ROLE_TABLES = {"platform_roles"}
# Tables introduced by the program/edition/project revision.
_PROGRAM_TABLES = {"programs", "editions", "projects"}


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
            # Head creates identity + session + role + program tables plus
            # Alembic's bookkeeping table.
            assert _IDENTITY_TABLES.issubset(tables)
            assert _SESSION_TABLES.issubset(tables)
            assert _ROLE_TABLES.issubset(tables)
            assert _PROGRAM_TABLES.issubset(tables)
            assert "alembic_version" in tables

            # The applied revision is the current head.
            script = ScriptDirectory.from_config(config)
            expected_head = script.get_current_head()
            applied = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert applied == expected_head
        assert expected_head == _SEED_EXEC_REVISION

        # Head state: programs has icon/is_standard and no kind; editions has no
        # status column; seed_executions tracking table exists.
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            program_cols = {c["name"] for c in inspect(conn).get_columns("programs")}
            edition_cols = {c["name"] for c in inspect(conn).get_columns("editions")}
        assert {"icon", "is_standard"}.issubset(program_cols)
        assert "kind" not in program_cols
        assert "status" not in edition_cols
        assert "seed_executions" in tables
    finally:
        engine.dispose()


def test_seed_executions_revision_upgrade_downgrade_roundtrip(empty_database_url: str) -> None:
    config = _alembic_config(empty_database_url)
    engine = create_engine(empty_database_url, future=True, poolclass=NullPool)
    try:
        command.upgrade(config, _SEED_EXEC_REVISION)
        with engine.connect() as conn:
            assert "seed_executions" in set(inspect(conn).get_table_names())

        command.downgrade(config, _SIMPLIFY_REVISION)
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            applied = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert "seed_executions" not in tables
        assert applied == _SIMPLIFY_REVISION
    finally:
        engine.dispose()


def test_simplify_revision_upgrade_downgrade_roundtrip(empty_database_url: str) -> None:
    config = _alembic_config(empty_database_url)
    engine = create_engine(empty_database_url, future=True, poolclass=NullPool)
    try:
        command.upgrade(config, _SIMPLIFY_REVISION)
        with engine.connect() as conn:
            cols = {c["name"] for c in inspect(conn).get_columns("programs")}
        assert "icon" in cols and "kind" not in cols

        # Downgrade one step restores the old columns (kind/status) and makes
        # dates nullable again.
        command.downgrade(config, _PROGRAM_REVISION)
        with engine.connect() as conn:
            program_cols = {c["name"] for c in inspect(conn).get_columns("programs")}
            edition_cols = {c["name"] for c in inspect(conn).get_columns("editions")}
            applied = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert "kind" in program_cols and "icon" not in program_cols
        assert "status" in edition_cols
        assert applied == _PROGRAM_REVISION
    finally:
        engine.dispose()


def test_simplify_revision_backfills_edition_dates_from_slug(empty_database_url: str) -> None:
    # Create a pre-simplify DB with an edition that has NULL dates and a
    # period-encoding slug; the migration must backfill annual/semester dates.
    config = _alembic_config(empty_database_url)
    engine = create_engine(empty_database_url, future=True, poolclass=NullPool)
    try:
        command.upgrade(config, _PROGRAM_REVISION)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO programs (id, slug, name, kind, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), 'gsoc', 'GSoC', 'gsoc', now(), now())"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO editions (id, program_id, slug, name, status, source, "
                    "created_at, updated_at) "
                    "SELECT gen_random_uuid(), id, '2026-2', 'E', 'completed', 'community', "
                    "now(), now() FROM programs WHERE slug = 'gsoc'"
                )
            )

        command.upgrade(config, _SIMPLIFY_REVISION)
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT starts_on, ends_on FROM editions WHERE slug = '2026-2'")
            ).one()
        # Second semester defaults.
        assert str(row[0]) == "2026-07-01"
        assert str(row[1]) == "2026-12-31"
    finally:
        engine.dispose()


def test_simplify_revision_fails_clearly_on_unbackfillable_edition(empty_database_url: str) -> None:
    config = _alembic_config(empty_database_url)
    engine = create_engine(empty_database_url, future=True, poolclass=NullPool)
    try:
        command.upgrade(config, _PROGRAM_REVISION)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO programs (id, slug, name, kind, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), 'gsoc', 'GSoC', 'gsoc', now(), now())"
                )
            )
            # NULL dates AND a slug that does not encode a period.
            conn.execute(
                text(
                    "INSERT INTO editions (id, program_id, slug, name, status, source, "
                    "created_at, updated_at) "
                    "SELECT gen_random_uuid(), id, 'legacy', 'E', 'completed', 'community', "
                    "now(), now() FROM programs WHERE slug = 'gsoc'"
                )
            )
        with pytest.raises(Exception, match="Cannot backfill edition dates"):
            command.upgrade(config, _SIMPLIFY_REVISION)
    finally:
        engine.dispose()


def test_roles_revision_upgrade_downgrade_roundtrip(empty_database_url: str) -> None:
    config = _alembic_config(empty_database_url)
    engine = create_engine(empty_database_url, future=True, poolclass=NullPool)
    try:
        # Upgrade to the roles revision: platform_roles exists.
        command.upgrade(config, _ROLES_REVISION)
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
        assert _ROLE_TABLES.issubset(tables)

        # Downgrade one step: platform_roles dropped, session tables remain.
        command.downgrade(config, _SESSIONS_REVISION)
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            applied = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert not (_ROLE_TABLES & tables)
        assert _SESSION_TABLES.issubset(tables)
        assert applied == _SESSIONS_REVISION
    finally:
        engine.dispose()


def test_program_revision_upgrade_downgrade_roundtrip(empty_database_url: str) -> None:
    config = _alembic_config(empty_database_url)
    engine = create_engine(empty_database_url, future=True, poolclass=NullPool)
    try:
        # Upgrade to the program revision: program/edition/project exist.
        command.upgrade(config, _PROGRAM_REVISION)
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
        assert _PROGRAM_TABLES.issubset(tables)

        # Downgrade one step: program tables dropped, role tables remain.
        command.downgrade(config, _ROLES_REVISION)
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            applied = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert not (_PROGRAM_TABLES & tables)
        assert _ROLE_TABLES.issubset(tables)
        assert applied == _ROLES_REVISION
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
