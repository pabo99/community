"""add seed_executions

Tracks which data seeds have successfully executed, so a seed runs exactly once
per database and re-running is a no-op (a later deletion of seeded data is not
silently recreated on the next deployment).

``seed_id`` is a stable, unique seed identifier. A row exists only after the
seed's database operations have committed atomically with the record.

Revision ID: 3d8b2f6c1a52
Revises: 2c7f1e9b4a30
Create Date: 2026-10-11 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d8b2f6c1a52"
down_revision: str | None = "2c7f1e9b4a30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "seed_executions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("seed_id", sa.String(length=128), nullable=False),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seed_executions")),
        sa.UniqueConstraint("seed_id", name="uq_seed_executions_seed_id"),
    )


def downgrade() -> None:
    op.drop_table("seed_executions")
