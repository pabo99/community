"""add sessions and oauth states

Creates the authentication persistence foundation:
- ``user_sessions``: PostgreSQL-backed server-side sessions. ``token_hash`` is
  the SHA-256 of the opaque cookie token (unique); FK to persons ON DELETE
  CASCADE; ``csrf_token`` for the double-submit CSRF pattern; absolute
  ``expires_at``.
- ``oauth_states``: short-lived, single-use, browser-bound OAuth state values;
  ``state_hash`` unique, ``binding_hash`` ties the callback to the initiating
  browser.

Reviewed against app.models metadata; the two agree exactly.

Revision ID: 8f8deb9d2cd7
Revises: 0b92c4c6d996
Create Date: 2026-10-08 20:08:37.041978

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f8deb9d2cd7"
down_revision: str | None = "0b92c4c6d996"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "oauth_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("binding_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oauth_states")),
        sa.UniqueConstraint("state_hash", name=op.f("uq_oauth_states_state_hash")),
    )
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("person_id", sa.UUID(), nullable=False),
        sa.Column("csrf_token", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["persons.id"],
            name=op.f("fk_user_sessions_person_id_persons"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_user_sessions_token_hash")),
    )
    op.create_index(
        op.f("ix_user_sessions_person_id"),
        "user_sessions",
        ["person_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_sessions_person_id"), table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("oauth_states")
