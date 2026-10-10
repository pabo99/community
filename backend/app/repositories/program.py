"""Persistence for Program, Edition, and Project.

Minimal create/get/list primitives for the M1-08 domain, sufficient for tests
and the upcoming M1-09 admin API. No business logic and no commits; the caller
owns the transaction boundary (see app/db/session.py).
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.edition import Edition
from app.models.program import Program
from app.models.project import Project


class ProgramRepository:
    """Data access for Program, Edition, and Project."""

    def __init__(self, session: Session) -> None:
        self._session = session

    # --- Program -------------------------------------------------------------

    def create_program(
        self, *, slug: str, name: str, kind: str, description: str | None = None
    ) -> Program:
        program = Program(slug=slug, name=name, kind=kind, description=description)
        self._session.add(program)
        return program

    def get_program(self, program_id: uuid.UUID) -> Program | None:
        return self._session.get(Program, program_id)

    def get_program_by_slug(self, slug: str) -> Program | None:
        return self._session.scalars(select(Program).where(Program.slug == slug)).one_or_none()

    def list_programs(self) -> list[Program]:
        return list(self._session.scalars(select(Program).order_by(Program.slug)).all())

    # --- Edition -------------------------------------------------------------

    def create_edition(
        self,
        *,
        program: Program,
        slug: str,
        name: str,
        status: str,
        starts_on: date | None = None,
        ends_on: date | None = None,
        source: str,
        external_id: str | None = None,
    ) -> Edition:
        edition = Edition(
            program=program,
            slug=slug,
            name=name,
            status=status,
            starts_on=starts_on,
            ends_on=ends_on,
            source=source,
            external_id=external_id,
        )
        self._session.add(edition)
        return edition

    def get_edition(self, edition_id: uuid.UUID) -> Edition | None:
        return self._session.get(Edition, edition_id)

    def list_editions_for_program(self, program_id: uuid.UUID) -> list[Edition]:
        stmt = select(Edition).where(Edition.program_id == program_id).order_by(Edition.slug)
        return list(self._session.scalars(stmt).all())

    # --- Project -------------------------------------------------------------

    def create_project(
        self, *, edition: Edition, slug: str, name: str, description: str | None = None
    ) -> Project:
        project = Project(edition=edition, slug=slug, name=name, description=description)
        self._session.add(project)
        return project

    def get_project(self, project_id: uuid.UUID) -> Project | None:
        return self._session.get(Project, project_id)

    def list_projects_for_edition(self, edition_id: uuid.UUID) -> list[Project]:
        stmt = select(Project).where(Project.edition_id == edition_id).order_by(Project.slug)
        return list(self._session.scalars(stmt).all())

    def flush(self) -> None:
        self._session.flush()
