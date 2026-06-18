"""LangGraph memory factories.

Two complementary mechanisms:
  • Checkpointer — persists a graph thread's state between turns (short-term /
    conversation memory). Backed by Postgres when configured, else in-memory.
  • Long-term store — cross-thread key/value memory with optional semantic index.

Both degrade gracefully: if the Postgres backends aren't installed/configured we
fall back to the in-memory implementations so the graph still runs.
"""

from __future__ import annotations

import logging

from ..config import get_settings

logger = logging.getLogger(__name__)


def get_checkpointer():
    """Return a LangGraph checkpointer for per-thread conversation persistence."""
    settings = get_settings()
    dsn = settings.memory_db_url
    if dsn and dsn.startswith("postgres"):
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            # Normalize SQLAlchemy-style DSN to a libpq one for psycopg.
            conn = dsn.replace("postgresql+psycopg://", "postgresql://")
            saver = PostgresSaver.from_conn_string(conn)
            saver.setup()
            return saver
        except Exception as exc:  # noqa: BLE001
            logger.warning("PostgresSaver unavailable (%s); using in-memory checkpointer", exc)

    from langgraph.checkpoint.memory import InMemorySaver

    return InMemorySaver()


def get_long_term_store():
    """Return a LangGraph BaseStore for cross-thread long-term memory."""
    settings = get_settings()
    dsn = settings.memory_db_url
    if dsn and dsn.startswith("postgres"):
        try:
            from langgraph.store.postgres import PostgresStore

            conn = dsn.replace("postgresql+psycopg://", "postgresql://")
            store = PostgresStore.from_conn_string(conn)
            store.setup()
            return store
        except Exception as exc:  # noqa: BLE001
            logger.warning("PostgresStore unavailable (%s); using in-memory store", exc)

    from langgraph.store.memory import InMemoryStore

    return InMemoryStore()
