"""baseline

Empty baseline revision. It creates no application/domain tables and requires
no PostgreSQL extensions. Running ``alembic upgrade head`` from an empty
database creates only Alembic's own ``alembic_version`` bookkeeping table and
reaches this baseline head. Domain tables arrive in later migrations
(M1-05 onward).

Revision ID: e049e161a164
Revises:
Create Date: 2026-10-04 19:48:26.204874

"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "e049e161a164"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op: baseline creates no schema objects."""


def downgrade() -> None:
    """No-op: nothing to undo for the baseline."""
