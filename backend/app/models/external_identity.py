"""ExternalIdentity domain model.

An ExternalIdentity links a Person to a provider-specific account
(product-design.md §3). The relationship is many-to-one with Person; a person
may hold several identities. Identities are keyed canonically on the stable
provider identifier (``provider_user_id``), never on the mutable username.

No credentials or tokens are stored here. omegaUp API tokens are ephemeral and
must never be persisted (AGENTS.md); ``verified_at`` is a timestamp, not a
secret.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Final

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.person import Person

# Supported identity providers. Stored as VARCHAR guarded by a CHECK constraint
# (not a native PostgreSQL ENUM) so adding a provider is a plain data change.
PROVIDER_GITHUB: Final = "github"
PROVIDER_OMEGAUP: Final = "omegaup"
PROVIDER_DISCORD: Final = "discord"
IDENTITY_PROVIDERS: Final = (PROVIDER_GITHUB, PROVIDER_OMEGAUP, PROVIDER_DISCORD)

_PROVIDERS_SQL: Final = ", ".join(f"'{p}'" for p in IDENTITY_PROVIDERS)


class ExternalIdentity(Base):
    """A provider-specific identity belonging to a Person."""

    __tablename__ = "external_identities"

    __table_args__ = (
        # provider must be one of the known values.
        CheckConstraint(
            f"provider IN ({_PROVIDERS_SQL})",
            name="provider_valid",
        ),
        # GitHub identities must carry a non-null, non-empty stable id. Other
        # providers may lack a stable id at creation time.
        CheckConstraint(
            "provider <> 'github' "
            "OR (provider_user_id IS NOT NULL AND length(provider_user_id) > 0)",
            name="github_requires_stable_id",
        ),
        # One platform identity per external account: unique on the stable id
        # within a provider, only when a stable id is present.
        Index(
            "uq_external_identities_provider_user_id",
            "provider",
            "provider_user_id",
            unique=True,
            postgresql_where=text("provider_user_id IS NOT NULL"),
        ),
        # Non-unique lookup support for username-based queries within a provider.
        Index(
            "ix_external_identities_provider_username",
            "provider",
            "username",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        index=True,
    )

    provider: Mapped[str] = mapped_column(String(32))
    # Stable external identifier where available (e.g. GitHub's numeric id).
    # This is the canonical lookup key and survives username changes.
    provider_user_id: Mapped[str | None] = mapped_column(String(255), default=None)
    # Current provider username/display identifier. Mutable; may be reassigned.
    username: Mapped[str | None] = mapped_column(String(255), default=None)
    # Verification metadata: when the association was verified (NULL = unverified).
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    # NOTE: `onupdate` is applied by SQLAlchemy on ORM flush, NOT a database
    # trigger. Writes that bypass the ORM will not update this column.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    person: Mapped[Person] = relationship(back_populates="identities")
