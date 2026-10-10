"""Program/Edition service.

Owns transaction boundaries for Program and Edition mutations: repositories
stage changes; the service commits once per operation. Unique-constraint
violations (including under concurrency) are caught inside a SAVEPOINT and
re-raised as a typed ``ConflictError`` so handlers can return 409 without
exposing raw PostgreSQL errors or leaving the session unusable.

Combined, cross-field validation that depends on existing stored state (the
edition date range after a partial update) lives here, not in the request
schema, and raises ``ValidationError`` which handlers map to 422.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.edition import Edition
from app.models.program import Program
from app.repositories.program import ProgramRepository


class ConflictError(Exception):
    """A uniqueness conflict (maps to HTTP 409)."""


class ValidationError(Exception):
    """A domain validation failure (maps to HTTP 422)."""


class ProgramService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ProgramRepository(session)

    # --- Program -------------------------------------------------------------

    def create_program(
        self, *, slug: str, name: str, kind: str, description: str | None
    ) -> Program:
        try:
            with self._session.begin_nested():
                program = self._repo.create_program(
                    slug=slug, name=name, kind=kind, description=description
                )
                self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(f"A program with slug '{slug}' already exists.") from exc
        self._session.commit()
        return program

    def update_program(
        self,
        program: Program,
        *,
        name: str | None,
        kind: str | None,
        description: str | None,
        provided: set[str],
    ) -> Program:
        if "name" in provided and name is not None:
            program.name = name
        if "kind" in provided and kind is not None:
            program.kind = kind
        if "description" in provided:
            program.description = description
        self._session.flush()
        self._session.commit()
        return program

    # --- Edition -------------------------------------------------------------

    def create_edition(
        self,
        *,
        program: Program,
        slug: str,
        name: str,
        status: str,
        starts_on: datetime.date | None,
        ends_on: datetime.date | None,
        source: str,
        external_id: str | None,
    ) -> Edition:
        try:
            with self._session.begin_nested():
                edition = self._repo.create_edition(
                    program=program,
                    slug=slug,
                    name=name,
                    status=status,
                    starts_on=starts_on,
                    ends_on=ends_on,
                    source=source,
                    external_id=external_id,
                )
                self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                f"An edition with slug '{slug}' already exists in this program, "
                "or the external reference is already in use."
            ) from exc
        self._session.commit()
        return edition

    def update_edition(
        self,
        edition: Edition,
        *,
        name: str | None,
        status: str | None,
        starts_on: datetime.date | None,
        ends_on: datetime.date | None,
        provided: set[str],
    ) -> Edition:
        # Resolve the effective date range: an omitted field keeps its stored
        # value; an explicitly provided field (including null) replaces it.
        effective_starts = starts_on if "starts_on" in provided else edition.starts_on
        effective_ends = ends_on if "ends_on" in provided else edition.ends_on
        if (
            effective_starts is not None
            and effective_ends is not None
            and effective_ends < effective_starts
        ):
            raise ValidationError("ends_on must be on or after starts_on.")

        if "name" in provided and name is not None:
            edition.name = name
        if "status" in provided and status is not None:
            edition.status = status
        if "starts_on" in provided:
            edition.starts_on = starts_on
        if "ends_on" in provided:
            edition.ends_on = ends_on

        self._session.flush()
        self._session.commit()
        return edition

    # --- Reads (no transaction) ---------------------------------------------

    def get_program(self, program_id: uuid.UUID) -> Program | None:
        return self._repo.get_program(program_id)

    def list_programs(self) -> list[Program]:
        return self._repo.list_programs()

    def get_edition(self, edition_id: uuid.UUID) -> Edition | None:
        return self._repo.get_edition(edition_id)

    def list_editions_for_program(self, program_id: uuid.UUID) -> list[Edition]:
        return self._repo.list_editions_for_program(program_id)
