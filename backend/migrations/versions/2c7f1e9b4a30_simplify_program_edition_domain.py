"""simplify program and edition domain

Reworks the Program/Edition domain (M1-10 redesign):

Programs:
- add ``icon`` (CHECK-constrained to a curated PrimeIcons allow-list),
- add ``is_standard`` (flags the seeded standard catalog),
- drop the redundant ``kind`` column + its CHECK (the catalog IS the set of
  program categories).

Editions:
- backfill any NULL ``starts_on``/``ends_on`` from the calendar period encoded
  by the slug (``YYYY``/``YYYY-1``/``YYYY-2``), then make both NOT NULL. If an
  existing edition has a NULL date AND a slug that does not encode a period,
  the migration FAILS CLEARLY rather than inventing a period.
- drop the manually stored ``status`` column + its CHECK (status is now a
  temporal value computed from the dates).

Provenance columns (``source``/``external_id``) and their constraints are kept
unchanged for future omegaUp integration.

Existing records are preserved (GSoC program and GSoC 2026 edition): identities
and relationships are untouched; only the new columns are populated and the
dropped columns removed.

Revision ID: 2c7f1e9b4a30
Revises: 1fa4c82c5a08
Create Date: 2026-10-11 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2c7f1e9b4a30"
down_revision: str | None = "1fa4c82c5a08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ICONS = (
    "github",
    "briefcase",
    "building",
    "heart",
    "users",
    "star",
    "code",
    "graduation-cap",
    "globe",
    "sun",
    "bolt",
    "folder",
)
_ICONS_SQL = ", ".join(f"'{i}'" for i in _ICONS)

# Standard-catalog slug -> default icon (used only to backfill existing rows;
# the authoritative catalog is seeded by the bootstrap command).
_STANDARD_ICON = {
    "gsoc": "github",
    "internships": "briefcase",
    "residencies": "building",
    "volunteering": "heart",
}


def upgrade() -> None:
    bind = op.get_bind()

    # --- programs: icon + is_standard, drop kind ---------------------------
    op.add_column("programs", sa.Column("icon", sa.String(length=64), nullable=True))
    op.add_column(
        "programs",
        sa.Column("is_standard", sa.Boolean(), server_default=sa.false(), nullable=False),
    )

    # Backfill icon: known standard slugs get their default; everything else
    # falls back to a neutral icon. Flag the standard catalog slugs.
    for slug, icon in _STANDARD_ICON.items():
        bind.execute(
            sa.text("UPDATE programs SET icon = :icon, is_standard = true WHERE slug = :slug"),
            {"icon": icon, "slug": slug},
        )
    bind.execute(sa.text("UPDATE programs SET icon = 'folder' WHERE icon IS NULL"))

    op.alter_column("programs", "icon", existing_type=sa.String(length=64), nullable=False)
    # Manage CHECK constraints by literal name via raw SQL: op.create/drop would
    # re-apply the metadata naming convention and double-prefix the name.
    bind.execute(
        sa.text(
            f"ALTER TABLE programs ADD CONSTRAINT ck_programs_icon_valid "
            f"CHECK (icon IN ({_ICONS_SQL}))"
        )
    )
    bind.execute(sa.text("ALTER TABLE programs DROP CONSTRAINT ck_programs_kind_valid"))
    op.drop_column("programs", "kind")
    # The is_standard server_default was only needed for the NOT NULL backfill.
    op.alter_column("programs", "is_standard", server_default=None)

    # --- editions: backfill dates, enforce NOT NULL, drop status -----------
    # Fail clearly if an edition has a NULL date and a slug that does not encode
    # a calendar period (we must not invent an incorrect period).
    unbackfillable = bind.execute(
        sa.text(
            "SELECT slug FROM editions "
            "WHERE (starts_on IS NULL OR ends_on IS NULL) "
            "AND slug !~ '^[0-9]{4}(-[12])?$'"
        )
    ).fetchall()
    if unbackfillable:
        slugs = ", ".join(row[0] for row in unbackfillable)
        raise RuntimeError(
            "Cannot backfill edition dates: these editions have missing dates and "
            f"a slug that does not encode a calendar period: {slugs}. "
            "Populate their dates manually before running this migration."
        )

    # Annual: Jan 1 - Dec 31. First semester (-1): Jan 1 - Jun 30.
    # Second semester (-2): Jul 1 - Dec 31. Only fills NULLs; never overwrites.
    bind.execute(
        sa.text(
            """
            UPDATE editions SET
                starts_on = COALESCE(
                    starts_on,
                    make_date(substring(slug from 1 for 4)::int,
                              CASE WHEN slug LIKE '%-2' THEN 7 ELSE 1 END, 1)
                ),
                ends_on = COALESCE(
                    ends_on,
                    CASE
                        WHEN slug LIKE '%-1'
                            THEN make_date(substring(slug from 1 for 4)::int, 6, 30)
                        WHEN slug LIKE '%-2'
                            THEN make_date(substring(slug from 1 for 4)::int, 12, 31)
                        ELSE make_date(substring(slug from 1 for 4)::int, 12, 31)
                    END
                )
            WHERE starts_on IS NULL OR ends_on IS NULL
            """
        )
    )

    op.alter_column("editions", "starts_on", existing_type=sa.Date(), nullable=False)
    op.alter_column("editions", "ends_on", existing_type=sa.Date(), nullable=False)

    bind.execute(sa.text("ALTER TABLE editions DROP CONSTRAINT ck_editions_status_valid"))
    op.drop_column("editions", "status")


def downgrade() -> None:
    bind = op.get_bind()
    # Re-add dropped columns with safe defaults. Original kind/status values are
    # not recoverable (they were discarded by design). CHECK constraints are
    # managed by literal name via raw SQL (see upgrade()).
    op.add_column(
        "editions",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
    )
    bind.execute(
        sa.text(
            "ALTER TABLE editions ADD CONSTRAINT ck_editions_status_valid "
            "CHECK (status IN ('draft', 'open', 'in_progress', 'completed', 'archived'))"
        )
    )
    op.alter_column("editions", "status", server_default=None)
    op.alter_column("editions", "ends_on", existing_type=sa.Date(), nullable=True)
    op.alter_column("editions", "starts_on", existing_type=sa.Date(), nullable=True)

    op.add_column(
        "programs",
        sa.Column("kind", sa.String(length=32), nullable=False, server_default="other"),
    )
    bind.execute(
        sa.text(
            "ALTER TABLE programs ADD CONSTRAINT ck_programs_kind_valid "
            "CHECK (kind IN ('gsoc', 'internship', 'residency', 'volunteer', 'other'))"
        )
    )
    op.alter_column("programs", "kind", server_default=None)
    bind.execute(sa.text("ALTER TABLE programs DROP CONSTRAINT ck_programs_icon_valid"))
    op.drop_column("programs", "is_standard")
    op.drop_column("programs", "icon")
