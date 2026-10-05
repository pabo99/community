"""SQLAlchemy declarative base and shared metadata.

A single :class:`Base` is the declarative base for all future ORM models. The
shared metadata carries an explicit constraint/index naming convention so that
Alembic autogeneration produces stable, predictable names once domain models
arrive (M1-05 onward). No models are defined here at M1-03.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Deterministic naming keeps migrations readable and autogenerate stable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
