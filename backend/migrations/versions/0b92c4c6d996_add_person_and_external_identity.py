"""add person and external identity

Creates the identity domain foundation: ``persons`` and ``external_identities``.

Constraints enforced in PostgreSQL:
- CHECK: provider is one of ('github', 'omegaup', 'discord').
- CHECK: github identities require a non-null, non-empty provider_user_id.
- FK external_identities.person_id -> persons.id ON DELETE CASCADE.
- Partial UNIQUE (provider, provider_user_id) WHERE provider_user_id IS NOT NULL.
- Non-unique index (provider, username) for lookups (usernames are mutable and
  intentionally NOT unique).

Reviewed against app.models metadata; the two agree exactly.

Revision ID: 0b92c4c6d996
Revises: e049e161a164
Create Date: 2026-10-08 19:36:51.981536

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0b92c4c6d996"
down_revision: str | None = "e049e161a164"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "persons",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_persons")),
    )
    op.create_table(
        "external_identities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("person_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
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
            "provider <> 'github' "
            "OR (provider_user_id IS NOT NULL AND length(provider_user_id) > 0)",
            name=op.f("ck_external_identities_github_requires_stable_id"),
        ),
        sa.CheckConstraint(
            "provider IN ('github', 'omegaup', 'discord')",
            name=op.f("ck_external_identities_provider_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["persons.id"],
            name=op.f("fk_external_identities_person_id_persons"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_external_identities")),
    )
    op.create_index(
        op.f("ix_external_identities_person_id"),
        "external_identities",
        ["person_id"],
        unique=False,
    )
    op.create_index(
        "ix_external_identities_provider_username",
        "external_identities",
        ["provider", "username"],
        unique=False,
    )
    op.create_index(
        "uq_external_identities_provider_user_id",
        "external_identities",
        ["provider", "provider_user_id"],
        unique=True,
        postgresql_where=sa.text("provider_user_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_external_identities_provider_user_id",
        table_name="external_identities",
        postgresql_where=sa.text("provider_user_id IS NOT NULL"),
    )
    op.drop_index(
        "ix_external_identities_provider_username",
        table_name="external_identities",
    )
    op.drop_index(
        op.f("ix_external_identities_person_id"),
        table_name="external_identities",
    )
    op.drop_table("external_identities")
    op.drop_table("persons")
