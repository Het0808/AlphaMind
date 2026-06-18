"""AlphaMind persistent memory.

Four kinds of long-lived memory, backed by PostgreSQL (SQLite for dev/tests):
  • User profile memory   — who the user is and how they like to invest
  • Company memory        — what we know/concluded about a ticker
  • Research history       — every past analysis, recallable later
  • Conversation history   — message log per thread

A vector memory enables semantic recall, and a hybrid retrieval strategy
(exact + recency + semantic) assembles cross-session context — so an earlier
"Analyze <company>" is remembered when the user later says "Compare with <peer>".

Only `schemas` is imported eagerly so `import alphamind.memory` stays light; the
SQLAlchemy-backed service is imported from `alphamind.memory.service`.
"""

from .schemas import (
    CompanyMemory,
    ConversationMessage,
    MemoryContext,
    MemoryHit,
    ResearchRecord,
    UserProfile,
)

__all__ = [
    "UserProfile",
    "CompanyMemory",
    "ResearchRecord",
    "ConversationMessage",
    "MemoryHit",
    "MemoryContext",
]
