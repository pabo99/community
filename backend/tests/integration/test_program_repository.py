"""Integration tests for ProgramService + ProgramRepository against PostgreSQL."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from app.models.program import Program
from app.repositories.program import ProgramRepository
from app.services.program import ConflictError, ProgramService, ValidationError
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def test_create_program_generates_slug(db_session: Session) -> None:
    service = ProgramService(db_session)
    program = service.create_program(
        name="Professional Internships", description=None, icon="briefcase"
    )
    assert program.slug == "professional-internships"
    assert ProgramRepository(db_session).get_program_by_slug("professional-internships") is program


def test_create_program_duplicate_slug_conflict(db_session: Session) -> None:
    service = ProgramService(db_session)
    service.create_program(name="GSoC", description=None, icon="github")
    with pytest.raises(ConflictError):
        service.create_program(name="GSoC", description=None, icon="github")


def test_create_edition_generates_slug_name_and_dates(db_session: Session) -> None:
    service = ProgramService(db_session)
    program = service.create_program(name="GSoC", description=None, icon="github")
    edition = service.create_edition(
        program=program, year=2026, period="annual", name=None, starts_on=None, ends_on=None
    )
    assert edition.slug == "2026"
    assert edition.name == "GSoC 2026"
    assert edition.starts_on == date(2026, 1, 1)
    assert edition.ends_on == date(2026, 12, 31)
    assert edition.source == "community"
    assert edition.external_id is None


def test_create_edition_semester_defaults(db_session: Session) -> None:
    service = ProgramService(db_session)
    program = service.create_program(name="Internships", description=None, icon="briefcase")
    h2 = service.create_edition(
        program=program,
        year=2026,
        period="second_semester",
        name=None,
        starts_on=None,
        ends_on=None,
    )
    assert h2.slug == "2026-2"
    assert h2.starts_on == date(2026, 7, 1)
    assert h2.ends_on == date(2026, 12, 31)


def test_create_edition_is_always_community(db_session: Session) -> None:
    # The admin service path never fabricates omegaUp provenance.
    service = ProgramService(db_session)
    program = service.create_program(name="GSoC", description=None, icon="github")
    edition = service.create_edition(
        program=program, year=2026, period="annual", name=None, starts_on=None, ends_on=None
    )
    assert edition.source == "community"


def test_create_edition_rejects_bad_date_override(db_session: Session) -> None:
    service = ProgramService(db_session)
    program = service.create_program(name="GSoC", description=None, icon="github")
    with pytest.raises(ValidationError):
        service.create_edition(
            program=program,
            year=2026,
            period="annual",
            name=None,
            starts_on=date(2026, 8, 1),
            ends_on=date(2026, 5, 1),
        )


def test_active_editions_and_count(db_session: Session) -> None:
    service = ProgramService(db_session)
    program = service.create_program(name="GSoC", description=None, icon="github")
    # Finished edition.
    service.create_edition(
        program=program,
        year=2000,
        period="annual",
        name=None,
        starts_on=date(2000, 1, 1),
        ends_on=date(2000, 12, 31),
    )
    # Far-future / wide edition that includes "today".
    service.create_edition(
        program=program,
        year=2026,
        period="annual",
        name=None,
        starts_on=date(2000, 1, 1),
        ends_on=date(2999, 12, 31),
    )
    assert service.edition_count(program.id) == 2
    active = service.active_editions(program.id)
    assert len(active) == 1
    assert active[0].slug == "2026"


def test_get_program_none_for_unknown(db_session: Session) -> None:
    assert ProgramService(db_session).get_program(uuid.uuid4()) is None


def test_update_program_edits_fields(db_session: Session) -> None:
    service = ProgramService(db_session)
    program = service.create_program(name="GSoC", description="old", icon="github")
    updated = service.update_program(
        program,
        name="Google Summer of Code",
        description=None,
        icon="code",
        provided={"name", "description", "icon"},
    )
    assert updated.name == "Google Summer of Code"
    assert updated.description is None
    assert updated.icon == "code"
    # Slug is immutable.
    assert updated.slug == "gsoc"


def test_repository_add_helpers_do_not_commit(db_session: Session) -> None:
    repo = ProgramRepository(db_session)
    repo.add_program(Program(slug="gsoc", name="GSoC", icon="github"))
    repo.flush()
    assert db_session.in_transaction()
