"""Standard program-catalog seed.

Populates the four standard programs and their initial 2026 editions:

- Google Summer of Code (``gsoc``): annual ``2026``.
- Professional Internships (``internships``): ``2026-1``, ``2026-2``.
- Professional Residencies (``residencies``): ``2026-1``, ``2026-2``.
- Volunteering (``volunteering``): annual ``2026``.

Within its single execution, the seed inserts only MISSING programs/editions
(matched by slug), so an existing GSoC program/edition is reused with its UUID
preserved and admin edits untouched. Because the runner records execution and
never re-runs a completed seed, deleting a standard program later is NOT undone
on the next deployment.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.edition import (
    EDITION_SOURCE_COMMUNITY,
    Edition,
    EditionPeriod,
    default_dates,
    slug_for,
)
from app.models.program import Program
from app.repositories.program import ProgramRepository
from app.seeds.runner import Seed

SEED_ID = "standard_catalog_v1"

_PERIOD_LABEL = {
    "annual": "",
    "first_semester": " (First semester)",
    "second_semester": " (Second semester)",
}


@dataclass(frozen=True)
class CatalogProgram:
    slug: str
    name: str
    icon: str
    editions: list[tuple[int, EditionPeriod]] = field(default_factory=list)


STANDARD_CATALOG: list[CatalogProgram] = [
    CatalogProgram("gsoc", "Google Summer of Code", "github", [(2026, "annual")]),
    CatalogProgram(
        "internships",
        "Professional Internships",
        "briefcase",
        [(2026, "first_semester"), (2026, "second_semester")],
    ),
    CatalogProgram(
        "residencies",
        "Professional Residencies",
        "building",
        [(2026, "first_semester"), (2026, "second_semester")],
    ),
    CatalogProgram("volunteering", "Volunteering", "heart", [(2026, "annual")]),
]


def seed_standard_catalog(session: Session) -> None:
    """Insert any missing standard programs/editions (no commit here)."""
    repo = ProgramRepository(session)
    for entry in STANDARD_CATALOG:
        program = repo.get_program_by_slug(entry.slug)
        if program is None:
            program = Program(slug=entry.slug, name=entry.name, icon=entry.icon, is_standard=True)
            repo.add_program(program)
            session.flush()
        elif not program.is_standard:
            program.is_standard = True

        for year, period in entry.editions:
            slug = slug_for(year, period)
            if repo.get_edition_by_slug(program.id, slug) is not None:
                continue
            starts_on, ends_on = default_dates(year, period)
            repo.add_edition(
                Edition(
                    program=program,
                    slug=slug,
                    name=f"{program.name} {year}{_PERIOD_LABEL[period]}",
                    starts_on=starts_on,
                    ends_on=ends_on,
                    source=EDITION_SOURCE_COMMUNITY,
                    external_id=None,
                )
            )
            session.flush()


STANDARD_CATALOG_SEED = Seed(seed_id=SEED_ID, run=seed_standard_catalog)
