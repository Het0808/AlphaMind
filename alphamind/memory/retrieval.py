"""Hybrid memory retrieval strategy.

A single similarity search is brittle for an investment assistant — the most
relevant memory ("the NVIDIA analysis I just ran") may not be the most
semantically similar to a terse follow-up ("compare with AMD"). So recall blends
three signals:

  1. EXACT      — the user's profile, and company memory for any explicit ticker.
  2. SEMANTIC   — vector similarity between the query and past memories.
  3. RECENCY    — the most recent research, so the latest analysis is always in
                  context even when semantic similarity is weak.

Results are de-duplicated (a record surfaced by both semantic and recency is not
repeated) and capped to a budget `k`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from ..config import get_settings
from .schemas import MemoryContext

if TYPE_CHECKING:  # avoid import cycle at runtime
    from .service import MemoryService


def recall(
    service: "MemoryService",
    query: str,
    *,
    user_id: Optional[str] = None,
    ticker: Optional[str] = None,
    k: Optional[int] = None,
) -> MemoryContext:
    k = k or get_settings().memory_recall_k

    # 1. EXACT recall.
    profile = service.get_user_profile(user_id)
    companies = []
    if ticker:
        company = service.get_company_memory(ticker)
        if company:
            companies.append(company)

    # 2. SEMANTIC recall (scoped to the user when known).
    semantic_hits = service.vector.search(query, k=k, user_id=user_id, min_score=0.0)

    # 3. RECENCY recall.
    recent = service.get_research_history(user_id=user_id, limit=k)

    # De-dup: drop semantic research hits already represented in recent research,
    # and drop recency items that exactly match the queried ticker context.
    recent_ids = {str(r.id) for r in recent}
    semantic_hits = [
        h for h in semantic_hits
        if not (h.kind == "research" and h.ref_id in recent_ids)
    ]

    return MemoryContext(
        query=query,
        user_profile=profile,
        companies=companies,
        recent_research=recent,
        semantic_hits=semantic_hits,
    )
