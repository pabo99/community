"""add program edition project

Creates the program-management domain: ``programs``, ``editions``, ``projects``.

Constraints enforced in PostgreSQL:
- programs: unique slug; CHECK kind in the known set.
- editions: FK -> programs ON DELETE RESTRICT (preserve history); unique
  (program_id, slug); CHECKs for status, source, ordered dates, and that a
  non-community source carries a non-empty external_id while community has
  none; partial UNIQUE (source, external_id) WHERE external_id IS NOT NULL.
- projects: FK -> editions ON DELETE RESTRICT (preserve history); unique
  (edition_id, slug).

Reviewed against app.models metadata; the two agree exactly.

Revision ID: 1fa4c82c5a08
Revises: 7c57bafdf5d6
Create Date: 2026-10-10 14:46:48.403976

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1fa4c82c5a08"
down_revision: str | None = "7c57bafdf5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "programs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('gsoc', 'internship', 'residency', 'volunteer', 'other')",
            name=op.f("ck_programs_kind_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_programs")),
        sa.UniqueConstraint("slug", name="uq_programs_slug"),
    )
    op.create_table(
        "editions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("program_id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(source = 'community' AND external_id IS NULL) "
            "OR (source <> 'community' AND external_id IS NOT NULL "
            "AND length(external_id) > 0)",
            name=op.f("ck_editions_external_id_matches_source"),
        ),
        sa.CheckConstraint(
            "source IN ('community', 'omegaup')",
            name=op.f("ck_editions_source_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'open', 'in_progress', 'completed', 'archived')",
            name=op.f("ck_editions_status_valid"),
        ),
        sa.CheckConstraint(
            "starts_on IS NULL OR ends_on IS NULL OR ends_on >= starts_on",
            name=op.f("ck_editions_dates_ordered"),
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["programs.id"],
            name=op.f("fk_editions_program_id_programs"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_editions")),
        sa.UniqueConstraint("program_id", "slug", name="uq_editions_program_id_slug"),
    )
    op.create_index(
        op.f("ix_editions_program_id"),
        "editions",
        ["program_id"],
        unique=False,
    )
    op.create_index(
        "uq_editions_source_external_id",
        "editions",
        ["source", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("edition_id", sa.UUID(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["edition_id"],
            ["editions.id"],
            name=op.f("fk_projects_edition_id_editions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("edition_id", "slug", name="uq_projects_edition_id_slug"),
    )
    op.create_index(
        op.f("ix_projects_edition_id"),
        "projects",
        ["edition_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_projects_edition_id"), table_name="projects")
    op.drop_table("projects")
    op.drop_index(
        "uq_editions_source_external_id",
        table_name="editions",
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )
    op.drop_index(op.f("ix_editions_program_id"), table_name="editions")
    op.drop_table("editions")
    op.drop_table("programs")
