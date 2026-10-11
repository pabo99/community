"""Integration tests for the Program/Edition domain against PostgreSQL.

Covers invariants, relationships, ON DELETE RESTRICT, provenance constraints,
icon CHECK, required dates, and the computed temporal status / period helpers.
"""

from __future__ import annotations

from datetime import date

import pytest
from app.models.edition import (
    EDITION_SOURCE_COMMUNITY,
    EDITION_SOURCE_OMEGAUP,
    Edition,
    InvalidEditionSlugError,
    compute_status,
    default_dates,
    period_of_slug,
    slug_for,
)
from app.models.program import Program
from app.models.project import Project
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def _program(session: Session, slug: str = "gsoc", icon: str = "github") -> Program:
    program = Program(slug=slug, name=slug.upper(), icon=icon)
    session.add(program)
    session.flush()
    return program


def _edition(
    session: Session,
    program: Program,
    *,
    slug: str = "2026",
    starts_on: date = date(2026, 1, 1),
    ends_on: date = date(2026, 12, 31),
    source: str = EDITION_SOURCE_COMMUNITY,
    external_id: str | None = None,
) -> Edition:
    edition = Edition(
        program=program,
        slug=slug,
        name=f"{program.name} {slug}",
        starts_on=starts_on,
        ends_on=ends_on,
        source=source,
        external_id=external_id,
    )
    session.add(edition)
    session.flush()
    return edition


# --- Period / status helpers -------------------------------------------------


def test_period_of_slug() -> None:
    assert period_of_slug("2026") == "annual"
    assert period_of_slug("2026-1") == "first_semester"
    assert period_of_slug("2026-2") == "second_semester"


def test_period_of_slug_rejects_invalid() -> None:
    with pytest.raises(InvalidEditionSlugError):
        period_of_slug("gsoc-2026")


def test_slug_for_and_default_dates() -> None:
    assert slug_for(2026, "annual") == "2026"
    assert slug_for(2026, "first_semester") == "2026-1"
    assert slug_for(2026, "second_semester") == "2026-2"
    assert default_dates(2026, "annual") == (date(2026, 1, 1), date(2026, 12, 31))
    assert default_dates(2026, "first_semester") == (date(2026, 1, 1), date(2026, 6, 30))
    assert default_dates(2026, "second_semester") == (date(2026, 7, 1), date(2026, 12, 31))


def test_compute_status() -> None:
    s, e = date(2026, 1, 1), date(2026, 12, 31)
    assert compute_status(s, e, reference=date(2025, 12, 31)) == "upcoming"
    assert compute_status(s, e, reference=date(2026, 1, 1)) == "active"
    assert compute_status(s, e, reference=date(2026, 12, 31)) == "active"
    assert compute_status(s, e, reference=date(2027, 1, 1)) == "finished"


# --- Relationships & invariants ---------------------------------------------


def test_program_edition_project_navigation(db_session: Session) -> None:
    program = _program(db_session)
    edition = _edition(db_session, program)
    db_session.add(Project(edition=edition, slug="compiler", name="Compiler"))
    db_session.flush()
    db_session.expire_all()

    reloaded = db_session.get(Program, program.id)
    assert reloaded is not None
    assert len(reloaded.editions) == 1
    assert reloaded.editions[0].period == "annual"
    assert len(reloaded.editions[0].projects) == 1


def test_program_slug_unique(db_session: Session) -> None:
    _program(db_session, slug="gsoc")
    db_session.add(Program(slug="gsoc", name="Dup", icon="folder"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_invalid_icon_rejected(db_session: Session) -> None:
    db_session.add(Program(slug="x", name="X", icon="not-an-icon"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_edition_slug_unique_per_program(db_session: Session) -> None:
    program = _program(db_session)
    _edition(db_session, program, slug="2026")
    db_session.add(
        Edition(
            program=program,
            slug="2026",
            name="Dup",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            source=EDITION_SOURCE_COMMUNITY,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_edition_dates_must_be_ordered(db_session: Session) -> None:
    program = _program(db_session)
    db_session.add(
        Edition(
            program=program,
            slug="2026",
            name="E",
            starts_on=date(2026, 12, 31),
            ends_on=date(2026, 1, 1),
            source=EDITION_SOURCE_COMMUNITY,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


# --- Provenance --------------------------------------------------------------


def test_community_edition_must_not_have_external_id(db_session: Session) -> None:
    program = _program(db_session)
    db_session.add(
        Edition(
            program=program,
            slug="2026",
            name="E",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            source=EDITION_SOURCE_COMMUNITY,
            external_id="x",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_omegaup_edition_requires_external_id(db_session: Session) -> None:
    program = _program(db_session)
    db_session.add(
        Edition(
            program=program,
            slug="2026",
            name="E",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            source=EDITION_SOURCE_OMEGAUP,
            external_id=None,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_source_external_id_unique_when_present(db_session: Session) -> None:
    p1 = _program(db_session, slug="gsoc")
    p2 = _program(db_session, slug="gsoc-mirror", icon="folder")
    _edition(db_session, p1, slug="2026", source=EDITION_SOURCE_OMEGAUP, external_id="omg-7")
    db_session.add(
        Edition(
            program=p2,
            slug="2026",
            name="Dup",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 12, 31),
            source=EDITION_SOURCE_OMEGAUP,
            external_id="omg-7",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


# --- ON DELETE RESTRICT ------------------------------------------------------


def test_deleting_program_with_editions_is_restricted(db_session: Session) -> None:
    program = _program(db_session)
    _edition(db_session, program)
    with pytest.raises(IntegrityError):
        db_session.execute(text("DELETE FROM programs WHERE id = :pid"), {"pid": program.id})


def test_deleting_edition_with_projects_is_restricted(db_session: Session) -> None:
    program = _program(db_session)
    edition = _edition(db_session, program)
    db_session.add(Project(edition=edition, slug="x", name="X"))
    db_session.flush()
    with pytest.raises(IntegrityError):
        db_session.execute(text("DELETE FROM editions WHERE id = :eid"), {"eid": edition.id})


def test_childless_delete_allowed(db_session: Session) -> None:
    program = _program(db_session)
    edition = _edition(db_session, program)
    db_session.execute(text("DELETE FROM editions WHERE id = :eid"), {"eid": edition.id})
    db_session.flush()
    db_session.execute(text("DELETE FROM programs WHERE id = :pid"), {"pid": program.id})
    db_session.flush()
    assert db_session.scalars(select(Program).where(Program.id == program.id)).all() == []
