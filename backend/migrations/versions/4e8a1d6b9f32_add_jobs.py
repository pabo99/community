"""add jobs

Creates the ``jobs`` table: the persistence foundation for PostgreSQL-backed
background work (technical-design.md §9, milestone-1 M1-11). This revision adds
only the table, its CHECK constraints, and the indexes used by later claiming
and recovery logic; no claiming/worker behavior is introduced here.

Schema notes:
- ``status`` CHECK-constrained to the lifecycle set
  (pending/running/succeeded/failed/retrying).
- ``claim_token`` is a per-claim UUID; result writes verify it in M1-11b so a
  stale worker cannot overwrite a newer owner's outcome.
- ``run_at`` drives eligibility and backoff; ``last_error`` is bounded (a short
  sanitized message, never a traceback or secret).
- Indexes support the claim query ``(status, run_at)`` and the stale-lease
  recovery sweep ``(status, locked_at)``.

Reviewed against app.models metadata; the two agree exactly.

Revision ID: 4e8a1d6b9f32
Revises: 3d8b2f6c1a52
Create Date: 2026-10-11 00:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4e8a1d6b9f32"
down_revision: str | None = "3d8b2f6c1a52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_type", sa.String(length=128), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column(
            "run_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("claim_token", sa.UUID(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=2000), nullable=True),
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
        sa.CheckConstraint("attempts >= 0", name=op.f("ck_jobs_attempts_non_negative")),
        sa.CheckConstraint(
            "last_error IS NULL OR length(last_error) <= 2000",
            name=op.f("ck_jobs_last_error_bounded"),
        ),
        sa.CheckConstraint("max_attempts >= 1", name=op.f("ck_jobs_max_attempts_positive")),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'retrying')",
            name=op.f("ck_jobs_status_valid"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index("ix_jobs_status_locked_at", "jobs", ["status", "locked_at"], unique=False)
    op.create_index("ix_jobs_status_run_at", "jobs", ["status", "run_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_jobs_status_run_at", table_name="jobs")
    op.drop_index("ix_jobs_status_locked_at", table_name="jobs")
    op.drop_table("jobs")
