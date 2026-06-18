"""Engine / session management.

Resolves a SQLAlchemy DSN from config — PostgreSQL when `MEMORY_DB_URL` is set,
otherwise a local SQLite file. Engines are cached per-URL so the SQLite file (or a
connection pool) is reused across the process.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from ..config import get_settings
from .models import Base


def resolve_dsn() -> str:
    settings = get_settings()
    if settings.memory_db_url:
        return settings.memory_db_url
    return f"sqlite:///{settings.memory_sqlite_path}"


@lru_cache
def get_engine(dsn: str | None = None) -> Engine:
    dsn = dsn or resolve_dsn()
    # SQLite needs cross-thread access disabled for use under a web server.
    connect_args = {"check_same_thread": False} if dsn.startswith("sqlite") else {}
    engine = create_engine(dsn, future=True, connect_args=connect_args)
    init_db(engine)
    return engine


def init_db(engine: Engine) -> None:
    """Create all memory tables if they don't exist (idempotent)."""
    Base.metadata.create_all(engine)
