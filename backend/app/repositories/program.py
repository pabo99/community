"""Persistence for Program, Edition, and Project.

Read/list primitives plus simple staged creates for the M1-10 domain. No
business logic (slug/date/provenance generation lives in the service) and no
commits; the caller owns the transaction boundary.
"""

from __future__ import annotations

import uuid

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

    def add_program(self, program: Program) -> Program:
        self._session.add(program)
        return program

    def get_program(self, program_id: uuid.UUID) -> Program | None:
        return self._session.get(Program, program_id)

    def get_program_by_slug(self, slug: str) -> Program | None:
        return self._session.scalars(select(Program).where(Program.slug == slug)).one_or_none()

    def list_programs(self) -> list[Program]:
        return list(self._session.scalars(select(Program).order_by(Program.slug)).all())

    # --- Edition -------------------------------------------------------------

    def add_edition(self, edition: Edition) -> Edition:
        self._session.add(edition)
        return edition

    def get_edition(self, edition_id: uuid.UUID) -> Edition | None:
        return self._session.get(Edition, edition_id)

    def get_edition_by_slug(self, program_id: uuid.UUID, slug: str) -> Edition | None:
        stmt = select(Edition).where(Edition.program_id == program_id, Edition.slug == slug)
        return self._session.scalars(stmt).one_or_none()

    def list_editions_for_program(self, program_id: uuid.UUID) -> list[Edition]:
        stmt = select(Edition).where(Edition.program_id == program_id).order_by(Edition.slug)
        return list(self._session.scalars(stmt).all())

    # --- Project -------------------------------------------------------------

    def add_project(self, project: Project) -> Project:
        self._session.add(project)
        return project

    def get_project(self, project_id: uuid.UUID) -> Project | None:
        return self._session.get(Project, project_id)

    def list_projects_for_edition(self, edition_id: uuid.UUID) -> list[Project]:
        stmt = select(Project).where(Project.edition_id == edition_id).order_by(Project.slug)
        return list(self._session.scalars(stmt).all())

    def flush(self) -> None:
        self._session.flush()
