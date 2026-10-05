"""Engine and session factory.

A single synchronous SQLAlchemy engine is created per process from application
settings (technical-design.md §4). The engine is created lazily and cached so
importing this module never requires a live database (``/health/live`` must
stay database-independent).
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine.

    ``pool_pre_ping`` recycles connections that the database may have dropped,
    so a transient outage does not surface as a stale-connection error.
    """
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


@lru_cache
def get_sessionmaker() -> sessionmaker[Session]:
    """Return the process-wide session factory bound to the engine."""
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
