"""Agent-facing wrappers over the MemoryService.

Heavy DB deps are imported lazily and errors degrade to an empty result, so the
graph runs fine when memory is disabled or the database is unreachable.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def recall_memory(query: str, *, user_id: Optional[str] = None, ticker: Optional[str] = None) -> Dict[str, Any]:
    """Recall prior context (profile, companies, recent + semantic research)."""
    try:
        from ..memory.service import get_memory_service

        ctx = get_memory_service().recall(query, user_id=user_id, ticker=ticker)
        return {"text": ctx.format(), "has_content": ctx.has_content(), "raw": ctx.model_dump()}
    except Exception as exc:  # noqa: BLE001
        logger.warning("recall_memory failed: %s", exc)
        return {"text": "", "has_content": False, "error": str(exc)}
