"""Seed-execution tracking model.

Records that a named data seed has successfully executed against this database.
A row is written in the same transaction as the seed's operations, so the two
commit atomically. The unique ``seed_id`` makes re-execution a no-op.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SeedExecution(Base):
    """A record that a data seed completed successfully."""

    __tablename__ = "seed_executions"

    __table_args__ = (UniqueConstraint("seed_id", name="uq_seed_executions_seed_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seed_id: Mapped[str] = mapped_column(String(128))
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
