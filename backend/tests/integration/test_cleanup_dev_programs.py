"""Tests for the development-only obsolete-program cleanup command."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest
from app.cli.cleanup_dev_programs import OBSOLETE_PROGRAM_SLUGS, cleanup, inspect_targets
from app.models.edition import Edition
from app.models.program import Program
from app.models.project import Project
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


@pytest.fixture
def db_session(migrated_engine: Engine) -> Iterator[Session]:
    connection = migrated_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


def _program(session: Session, slug: str, *, is_standard: bool = False) -> Program:
    program = Program(slug=slug, name=slug.upper(), icon="folder", is_standard=is_standard)
    session.add(program)
    session.flush()
    return program


def test_targets_only_the_two_exact_slugs() -> None:
    assert OBSOLETE_PROGRAM_SLUGS == ("2026", "internship")


def test_dry_run_makes_no_changes(db_session: Session) -> None:
    _program(db_session, "2026")
    _program(db_session, "internship")
    db_session.flush()

    deleted = cleanup(db_session, confirm=False, log=lambda _m: None)
    assert deleted == 0
    assert db_session.scalars(select(Program).where(Program.slug == "2026")).one_or_none()
    assert db_session.scalars(select(Program).where(Program.slug == "internship")).one_or_none()


def test_confirm_deletes_obsolete_programs_and_empty_editions(db_session: Session) -> None:
    _program(db_session, "2026")  # zero editions
    internship = _program(db_session, "internship")
    db_session.add(
        Edition(
            program=internship,
            slug="2025",
            name="Old",
            starts_on=date(2025, 1, 1),
            ends_on=date(2025, 12, 31),
            source="community",
        )
    )
    db_session.flush()

    deleted = cleanup(db_session, confirm=True, log=lambda _m: None)
    assert deleted == 2
    assert db_session.scalars(select(Program).where(Program.slug == "2026")).one_or_none() is None
    assert (
        db_session.scalars(select(Program).where(Program.slug == "internship")).one_or_none()
        is None
    )


def test_refuses_when_edition_has_projects(db_session: Session) -> None:
    internship = _program(db_session, "internship")
    edition = Edition(
        program=internship,
        slug="2025",
        name="Old",
        starts_on=date(2025, 1, 1),
        ends_on=date(2025, 12, 31),
        source="community",
    )
    db_session.add(edition)
    db_session.flush()
    db_session.add(Project(edition=edition, slug="p1", name="P1"))
    db_session.flush()

    deleted = cleanup(db_session, confirm=True, log=lambda _m: None)
    assert deleted == 0  # blocked by dependent project
    assert (
        db_session.scalars(select(Program).where(Program.slug == "internship")).one_or_none()
        is not None
    )


def test_never_touches_standard_programs(db_session: Session) -> None:
    # Even a standard program that somehow had an obsolete slug is refused.
    _program(db_session, "internship", is_standard=True)
    db_session.flush()
    plan = inspect_targets(db_session, log=lambda _m: None)
    assert plan["internship"].blocked is True

    deleted = cleanup(db_session, confirm=True, log=lambda _m: None)
    assert deleted == 0
    assert (
        db_session.scalars(select(Program).where(Program.slug == "internship")).one_or_none()
        is not None
    )


def test_ignores_other_non_standard_programs(db_session: Session) -> None:
    # A non-standard program with a different slug is never considered.
    _program(db_session, "random-dev-program")
    db_session.flush()
    cleanup(db_session, confirm=True, log=lambda _m: None)
    assert (
        db_session.scalars(
            select(Program).where(Program.slug == "random-dev-program")
        ).one_or_none()
        is not None
    )
