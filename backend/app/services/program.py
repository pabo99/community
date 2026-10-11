"""Program/Edition service.

Owns transaction boundaries for Program and Edition mutations: repositories
stage changes; the service commits once per operation. Unique-constraint
violations (including under concurrency) are caught inside a SAVEPOINT and
re-raised as ``ConflictError`` (HTTP 409). Domain validation that depends on
stored state raises ``ValidationError`` (HTTP 422).

Program slugs are generated from the name. Edition slug/name/default dates are
generated from a year + period. Manually created editions are always
``source=community`` (the admin path can never fabricate omegaUp provenance).
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.edition import (
    EDITION_SOURCE_COMMUNITY,
    Edition,
    EditionPeriod,
    compute_status,
    default_dates,
    slug_for,
)
from app.models.program import Program, slugify
from app.repositories.program import ProgramRepository


class ConflictError(Exception):
    """A uniqueness conflict (maps to HTTP 409)."""


class ValidationError(Exception):
    """A domain validation failure (maps to HTTP 422)."""


_PERIOD_LABEL = {
    "annual": "",
    "first_semester": " (First semester)",
    "second_semester": " (Second semester)",
}


class ProgramService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ProgramRepository(session)

    # --- Program -------------------------------------------------------------

    def create_program(self, *, name: str, description: str | None, icon: str) -> Program:
        slug = slugify(name)
        try:
            with self._session.begin_nested():
                program = Program(slug=slug, name=name, description=description, icon=icon)
                self._session.add(program)
                self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                f"A program with slug '{slug}' already exists. Choose a different name."
            ) from exc
        self._session.commit()
        return program

    def update_program(
        self,
        program: Program,
        *,
        name: str | None,
        description: str | None,
        icon: str | None,
        provided: set[str],
    ) -> Program:
        if "name" in provided and name is not None:
            program.name = name
        if "description" in provided:
            program.description = description
        if "icon" in provided and icon is not None:
            program.icon = icon
        self._session.flush()
        self._session.commit()
        return program

    # --- Edition -------------------------------------------------------------

    def create_edition(
        self,
        *,
        program: Program,
        year: int,
        period: EditionPeriod,
        name: str | None,
        starts_on: datetime.date | None,
        ends_on: datetime.date | None,
    ) -> Edition:
        slug = slug_for(year, period)
        default_start, default_end = default_dates(year, period)
        resolved_start = starts_on or default_start
        resolved_end = ends_on or default_end
        if resolved_end < resolved_start:
            raise ValidationError("ends_on must be on or after starts_on.")
        resolved_name = name or f"{program.name} {year}{_PERIOD_LABEL[period]}"

        try:
            with self._session.begin_nested():
                edition = Edition(
                    program=program,
                    slug=slug,
                    name=resolved_name,
                    starts_on=resolved_start,
                    ends_on=resolved_end,
                    # Manual editions are always community-sourced; the admin
                    # path can never set omegaUp provenance.
                    source=EDITION_SOURCE_COMMUNITY,
                    external_id=None,
                )
                self._session.add(edition)
                self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(f"An edition '{slug}' already exists for this program.") from exc
        self._session.commit()
        return edition

    def update_edition(
        self,
        edition: Edition,
        *,
        name: str | None,
        starts_on: datetime.date | None,
        ends_on: datetime.date | None,
        provided: set[str],
    ) -> Edition:
        effective_start = starts_on if "starts_on" in provided else edition.starts_on
        effective_end = ends_on if "ends_on" in provided else edition.ends_on
        # Dates remain required; clearing to null is not allowed.
        if effective_start is None or effective_end is None:
            raise ValidationError("starts_on and ends_on are required.")
        if effective_end < effective_start:
            raise ValidationError("ends_on must be on or after starts_on.")

        if "name" in provided and name is not None:
            edition.name = name
        if "starts_on" in provided and starts_on is not None:
            edition.starts_on = starts_on
        if "ends_on" in provided and ends_on is not None:
            edition.ends_on = ends_on

        self._session.flush()
        self._session.commit()
        return edition

    # --- Delete (empty-only) -------------------------------------------------

    def delete_program(self, program: Program) -> None:
        """Delete a program only when it has no editions.

        No cascading deletion of business data; a non-empty program raises
        ConflictError (HTTP 409). Enforced here within the transaction, backed
        by the ON DELETE RESTRICT foreign key.
        """
        if self.edition_count(program.id) > 0:
            raise ConflictError(
                "This program has editions and cannot be deleted. Delete its editions first."
            )
        try:
            with self._session.begin_nested():
                self._session.delete(program)
                self._session.flush()
        except IntegrityError as exc:
            # Defensive: a concurrent insert of a dependent row.
            raise ConflictError(
                "This program has dependent records and cannot be deleted."
            ) from exc
        self._session.commit()

    def delete_edition(self, edition: Edition) -> None:
        """Delete an edition only when it has no projects/dependent records."""
        projects = self._repo.list_projects_for_edition(edition.id)
        if projects:
            raise ConflictError("This edition has dependent records and cannot be deleted.")
        try:
            with self._session.begin_nested():
                self._session.delete(edition)
                self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "This edition has dependent records and cannot be deleted."
            ) from exc
        self._session.commit()

    # --- Reads ---------------------------------------------------------------

    def get_program(self, program_id: uuid.UUID) -> Program | None:
        return self._repo.get_program(program_id)

    def list_programs(self) -> list[Program]:
        return self._repo.list_programs()

    def edition_count(self, program_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Edition).where(Edition.program_id == program_id)
        return int(self._session.scalar(stmt) or 0)

    def active_editions(self, program_id: uuid.UUID) -> list[Edition]:
        """All editions of a program whose computed status is 'active'."""
        editions = self._repo.list_editions_for_program(program_id)
        return [e for e in editions if compute_status(e.starts_on, e.ends_on) == "active"]

    def get_edition(self, edition_id: uuid.UUID) -> Edition | None:
        return self._repo.get_edition(edition_id)

    def list_editions_for_program(self, program_id: uuid.UUID) -> list[Edition]:
        return self._repo.list_editions_for_program(program_id)
