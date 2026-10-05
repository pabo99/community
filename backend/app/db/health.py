"""Database connectivity probe for readiness checks.

This is a lightweight connectivity check, not a domain repository. It executes
a trivial ``SELECT 1`` and reports a boolean, deliberately swallowing the
underlying exception so callers never leak driver/connection details into
responses or logs.
"""

from __future__ import annotations

from sqlalchemy import text

from app.db.engine import get_engine


def database_is_available() -> bool:
    """Return True if a trivial query against PostgreSQL succeeds."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
