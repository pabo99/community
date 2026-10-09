"""add platform roles

Creates ``platform_roles``: platform-wide authorization grants.
- ``role`` is CHECK-constrained to the known set (only 'superadmin' at M1-07).
- FK to persons ON DELETE CASCADE.
- UNIQUE (person_id, role) makes grants idempotent at the database level and
  prevents duplicate role rows under concurrency.

Reviewed against app.models metadata; the two agree exactly.

Revision ID: 7c57bafdf5d6
Revises: 8f8deb9d2cd7
Create Date: 2026-10-09 15:02:35.391137

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c57bafdf5d6"
down_revision: str | None = "8f8deb9d2cd7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_roles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("person_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('superadmin')",
            name=op.f("ck_platform_roles_role_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["persons.id"],
            name=op.f("fk_platform_roles_person_id_persons"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_roles")),
        sa.UniqueConstraint("person_id", "role", name="uq_platform_roles_person_id_role"),
    )
    op.create_index(
        op.f("ix_platform_roles_person_id"),
        "platform_roles",
        ["person_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_platform_roles_person_id"), table_name="platform_roles")
    op.drop_table("platform_roles")
