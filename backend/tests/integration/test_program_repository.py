"""Integration tests for ProgramRepository against PostgreSQL."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from app.models.edition import EDITION_SOURCE_COMMUNITY, EDITION_STATUS_OPEN
from app.models.program import PROGRAM_KIND_INTERNSHIP
from app.repositories.program import ProgramRepository
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def test_create_and_get_program(db_session: Session) -> None:
    repo = ProgramRepository(db_session)
    program = repo.create_program(
        slug="internship", name="Internship", kind=PROGRAM_KIND_INTERNSHIP
    )
    repo.flush()

    assert repo.get_program(program.id) is program
    assert repo.get_program_by_slug("internship") is program
    assert repo.get_program(uuid.uuid4()) is None


def test_create_edition_and_project_and_list(db_session: Session) -> None:
    repo = ProgramRepository(db_session)
    program = repo.create_program(slug="gsoc", name="GSoC", kind="gsoc")
    edition = repo.create_edition(
        program=program,
        slug="2027",
        name="GSoC 2027",
        status=EDITION_STATUS_OPEN,
        starts_on=date(2027, 5, 1),
        ends_on=date(2027, 8, 1),
        source=EDITION_SOURCE_COMMUNITY,
    )
    repo.create_project(edition=edition, slug="compiler", name="Compiler")
    repo.create_project(edition=edition, slug="frontend", name="Frontend")
    repo.flush()

    assert [e.slug for e in repo.list_editions_for_program(program.id)] == ["2027"]
    projects = repo.list_projects_for_edition(edition.id)
    assert {p.slug for p in projects} == {"compiler", "frontend"}


def test_list_programs_ordered(db_session: Session) -> None:
    repo = ProgramRepository(db_session)
    repo.create_program(slug="volunteer", name="V", kind="volunteer")
    repo.create_program(slug="gsoc", name="G", kind="gsoc")
    repo.flush()

    assert [p.slug for p in repo.list_programs()] == ["gsoc", "volunteer"]


def test_repository_does_not_commit(db_session: Session) -> None:
    repo = ProgramRepository(db_session)
    repo.create_program(slug="gsoc", name="G", kind="gsoc")
    repo.flush()
    assert db_session.in_transaction()
