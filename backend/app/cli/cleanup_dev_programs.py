"""Development-only cleanup of specific obsolete program records.

This targets EXACTLY two obsolete, manually created development programs by
slug: ``2026`` and ``internship`` (singular). These are leftovers from early
manual testing and are distinct from the four standard programs.

Safety:
- Dry-run by default: reports the exact records and their dependencies and
  makes no changes. Destructive execution requires ``--confirm``.
- Refuses to delete a program that has dependent business data beyond empty
  editions (projects or any editions with projects). Programs with only empty
  editions are removed by deleting those empty editions first, then the program.
- Never uses broad conditions (e.g. "all non-standard programs"); only the two
  explicit slugs are ever considered.
- This command is NEVER invoked by seeds, migrations, startup, or normal
  deployment. It must be run explicitly and only in development.

It is intentionally not wired into the Makefile's standard workflow.
"""

from __future__ import annotations

import sys
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.engine import get_sessionmaker
from app.models.edition import Edition
from app.models.program import Program
from app.models.project import Project

# The exact, explicit set of obsolete development slugs this command may touch.
OBSOLETE_PROGRAM_SLUGS: tuple[str, ...] = ("2026", "internship")


@dataclass
class TargetPlan:
    """What the cleanup would do for one obsolete slug."""

    slug: str
    program: Program
    editions: list[Edition] = field(default_factory=list)
    blocked: bool = False
    reason: str = ""


@contextmanager
def _session_scope() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()


def _edition_project_count(session: Session, edition_id: uuid.UUID) -> int:
    return len(session.scalars(select(Project).where(Project.edition_id == edition_id)).all())


def inspect_targets(
    session: Session, *, log: Callable[[str], None] = print
) -> dict[str, TargetPlan]:
    """Report the exact obsolete records and their dependencies, keyed by slug."""
    plan: dict[str, TargetPlan] = {}
    for slug in OBSOLETE_PROGRAM_SLUGS:
        program = session.scalars(select(Program).where(Program.slug == slug)).one_or_none()
        if program is None:
            log(f"Program '{slug}': not present; nothing to do.")
            continue
        if program.is_standard:
            # Never touch a standard program, even if it somehow shares a slug.
            log(f"Program '{slug}': is a STANDARD program; refusing to touch it.")
            plan[slug] = TargetPlan(
                slug=slug, program=program, blocked=True, reason="standard program"
            )
            continue

        editions = list(
            session.scalars(select(Edition).where(Edition.program_id == program.id)).all()
        )
        with_projects = [e for e in editions if _edition_project_count(session, e.id) > 0]
        blocked = len(with_projects) > 0
        reason = f"{len(with_projects)} edition(s) contain projects" if blocked else ""
        log(
            f"Program '{slug}' (id={program.id}): {len(editions)} edition(s), "
            f"{len(with_projects)} with dependent projects. "
            + ("WOULD BE BLOCKED." if blocked else "Eligible for deletion.")
        )
        for e in editions:
            count = _edition_project_count(session, e.id)
            log(f"    edition '{e.slug}' (id={e.id}): projects={count}")
        plan[slug] = TargetPlan(
            slug=slug, program=program, editions=editions, blocked=blocked, reason=reason
        )
    return plan


def cleanup(session: Session, *, confirm: bool, log: Callable[[str], None] = print) -> int:
    """Report (and, if confirmed, delete) the obsolete records. Returns count."""
    plan = inspect_targets(session, log=log)
    if not confirm:
        log("")
        log("DRY RUN: no changes made. Re-run with --confirm to delete.")
        return 0

    deleted = 0
    for slug, target in plan.items():
        if target.blocked:
            log(f"Program '{slug}': blocked ({target.reason}); skipped.")
            continue
        for edition in target.editions:
            session.delete(edition)
        session.flush()
        session.delete(target.program)
        session.flush()
        deleted += 1
        log(f"Program '{slug}': deleted.")

    session.commit()
    log(f"Cleanup complete: {deleted} program(s) deleted.")
    return deleted


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    confirm = "--confirm" in args
    with _session_scope() as session:
        cleanup(session, confirm=confirm)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
