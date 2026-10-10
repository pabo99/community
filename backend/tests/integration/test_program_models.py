"""Integration tests for the Program/Edition/Project domain against PostgreSQL.

Covers invariants, relationships, ON DELETE RESTRICT behavior, and edition
provenance constraints.
"""

from __future__ import annotations

from datetime import date

import pytest
from app.models.edition import (
    EDITION_SOURCE_COMMUNITY,
    EDITION_SOURCE_OMEGAUP,
    EDITION_STATUS_DRAFT,
    Edition,
)
from app.models.program import PROGRAM_KIND_GSOC, Program
from app.models.project import Project
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def _program(session: Session, slug: str = "gsoc") -> Program:
    program = Program(slug=slug, name="GSoC", kind=PROGRAM_KIND_GSOC)
    session.add(program)
    session.flush()
    return program


def _edition(
    session: Session,
    program: Program,
    *,
    slug: str = "2027",
    status: str = EDITION_STATUS_DRAFT,
    source: str = EDITION_SOURCE_COMMUNITY,
    external_id: str | None = None,
    starts_on: date | None = None,
    ends_on: date | None = None,
) -> Edition:
    edition = Edition(
        program=program,
        slug=slug,
        name=f"GSoC {slug}",
        status=status,
        source=source,
        external_id=external_id,
        starts_on=starts_on,
        ends_on=ends_on,
    )
    session.add(edition)
    session.flush()
    return edition


# --- Relationships -----------------------------------------------------------


def test_program_edition_project_navigation(db_session: Session) -> None:
    program = _program(db_session)
    edition = _edition(db_session, program)
    db_session.add(Project(edition=edition, slug="compiler", name="Compiler work"))
    db_session.flush()
    db_session.expire_all()

    reloaded = db_session.get(Program, program.id)
    assert reloaded is not None
    assert len(reloaded.editions) == 1
    assert len(reloaded.editions[0].projects) == 1
    assert reloaded.editions[0].projects[0].edition.program.id == program.id


# --- Uniqueness invariants ---------------------------------------------------


def test_program_slug_is_unique(db_session: Session) -> None:
    _program(db_session, slug="gsoc")
    db_session.add(Program(slug="gsoc", name="Dup", kind=PROGRAM_KIND_GSOC))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_edition_slug_unique_per_program(db_session: Session) -> None:
    program = _program(db_session)
    _edition(db_session, program, slug="2027")
    db_session.add(
        Edition(
            program=program,
            slug="2027",
            name="Dup",
            status=EDITION_STATUS_DRAFT,
            source=EDITION_SOURCE_COMMUNITY,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_edition_same_slug_different_program_allowed(db_session: Session) -> None:
    p1 = _program(db_session, slug="gsoc")
    p2 = _program(db_session, slug="internship")
    _edition(db_session, p1, slug="2027")
    _edition(db_session, p2, slug="2027")  # must not raise


def test_project_slug_unique_per_edition(db_session: Session) -> None:
    program = _program(db_session)
    edition = _edition(db_session, program)
    db_session.add(Project(edition=edition, slug="x", name="X"))
    db_session.flush()
    db_session.add(Project(edition=edition, slug="x", name="Dup"))
    with pytest.raises(IntegrityError):
        db_session.flush()


# --- CHECK constraints -------------------------------------------------------


def test_invalid_program_kind_rejected(db_session: Session) -> None:
    db_session.add(Program(slug="p", name="P", kind="bootcamp"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_invalid_edition_status_rejected(db_session: Session) -> None:
    program = _program(db_session)
    db_session.add(
        Edition(
            program=program, slug="2027", name="E", status="paused", source=EDITION_SOURCE_COMMUNITY
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_edition_dates_must_be_ordered(db_session: Session) -> None:
    program = _program(db_session)
    db_session.add(
        Edition(
            program=program,
            slug="2027",
            name="E",
            status=EDITION_STATUS_DRAFT,
            source=EDITION_SOURCE_COMMUNITY,
            starts_on=date(2027, 6, 1),
            ends_on=date(2027, 5, 1),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_edition_dates_ordered_ok(db_session: Session) -> None:
    program = _program(db_session)
    _edition(
        db_session,
        program,
        starts_on=date(2027, 5, 1),
        ends_on=date(2027, 8, 1),
    )  # must not raise


# --- Provenance --------------------------------------------------------------


def test_community_edition_must_not_have_external_id(db_session: Session) -> None:
    program = _program(db_session)
    db_session.add(
        Edition(
            program=program,
            slug="2027",
            name="E",
            status=EDITION_STATUS_DRAFT,
            source=EDITION_SOURCE_COMMUNITY,
            external_id="omg-1",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_omegaup_edition_requires_non_empty_external_id(db_session: Session) -> None:
    program = _program(db_session)
    db_session.add(
        Edition(
            program=program,
            slug="2027",
            name="E",
            status=EDITION_STATUS_DRAFT,
            source=EDITION_SOURCE_OMEGAUP,
            external_id=None,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_omegaup_edition_rejects_empty_external_id(db_session: Session) -> None:
    program = _program(db_session)
    db_session.add(
        Edition(
            program=program,
            slug="2027",
            name="E",
            status=EDITION_STATUS_DRAFT,
            source=EDITION_SOURCE_OMEGAUP,
            external_id="",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_omegaup_edition_with_external_id_is_accepted(db_session: Session) -> None:
    program = _program(db_session)
    _edition(db_session, program, source=EDITION_SOURCE_OMEGAUP, external_id="omg-42")


def test_source_external_id_unique_when_present(db_session: Session) -> None:
    p1 = _program(db_session, slug="gsoc")
    p2 = _program(db_session, slug="gsoc-mirror")
    _edition(db_session, p1, slug="2027", source=EDITION_SOURCE_OMEGAUP, external_id="omg-7")
    db_session.add(
        Edition(
            program=p2,
            slug="2027",
            name="Dup",
            status=EDITION_STATUS_DRAFT,
            source=EDITION_SOURCE_OMEGAUP,
            external_id="omg-7",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_multiple_community_editions_without_external_id_allowed(db_session: Session) -> None:
    # NULL external_id is excluded from the partial unique index.
    p1 = _program(db_session, slug="a")
    p2 = _program(db_session, slug="b")
    _edition(db_session, p1, slug="2027")
    _edition(db_session, p2, slug="2027")  # must not raise


# --- ON DELETE RESTRICT ------------------------------------------------------


def test_deleting_program_with_editions_is_restricted(db_session: Session) -> None:
    program = _program(db_session)
    _edition(db_session, program)
    # RESTRICT: the DELETE itself raises a foreign-key violation.
    with pytest.raises(IntegrityError):
        db_session.execute(text("DELETE FROM programs WHERE id = :pid"), {"pid": program.id})


def test_deleting_edition_with_projects_is_restricted(db_session: Session) -> None:
    program = _program(db_session)
    edition = _edition(db_session, program)
    db_session.add(Project(edition=edition, slug="x", name="X"))
    db_session.flush()
    with pytest.raises(IntegrityError):
        db_session.execute(text("DELETE FROM editions WHERE id = :eid"), {"eid": edition.id})


def test_deleting_childless_program_and_edition_is_allowed(db_session: Session) -> None:
    program = _program(db_session)
    edition = _edition(db_session, program)
    # Delete leaf-first: edition (no projects), then program (no editions).
    db_session.execute(text("DELETE FROM editions WHERE id = :eid"), {"eid": edition.id})
    db_session.flush()
    db_session.execute(text("DELETE FROM programs WHERE id = :pid"), {"pid": program.id})
    db_session.flush()
    assert db_session.scalars(select(Program).where(Program.id == program.id)).all() == []
