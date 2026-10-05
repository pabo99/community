"""Request-scoped database session dependency.

``get_db`` owns only the Session lifecycle: it creates/yields one request-scoped
Session, rolls back if an exception escapes, and always closes the Session. It
does NOT commit on success. Transaction boundaries are owned by future
service/use-case layers that coordinate business operations; repositories
receive a Session and may query/add/flush but do not commit as a general rule.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.db.engine import get_sessionmaker


def get_db() -> Iterator[Session]:
    """Yield a request-scoped Session with rollback-on-error and always-close."""
    session = get_sessionmaker()()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
