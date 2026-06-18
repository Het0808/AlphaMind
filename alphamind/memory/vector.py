"""Vector memory — semantic add/search over stored embeddings.

Embeddings come from the shared OpenAI factory (injectable for tests). Similarity
is cosine, computed in Python over candidate rows so the same code works on SQLite
and PostgreSQL. Embedding failures are swallowed (the structured record is still
written) so memory never hard-fails a run.
"""

from __future__ import annotations

import logging
import math
from typing import Callable, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from .models import VectorRow
from .schemas import MemoryHit

logger = logging.getLogger(__name__)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class VectorMemory:
    def __init__(self, session_factory: sessionmaker, embedder_provider: Callable[[], object]):
        self._Session: sessionmaker = session_factory
        self._embedder_provider = embedder_provider

    def _embed(self, text: str) -> Optional[List[float]]:
        try:
            return self._embedder_provider().embed_query(text)
        except Exception as exc:  # noqa: BLE001 - embeddings are best-effort
            logger.warning("Embedding failed; skipping vector index: %s", exc)
            return None

    def add(
        self,
        *,
        kind: str,
        text: str,
        ref_id: Optional[str] = None,
        user_id: Optional[str] = None,
        ticker: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> bool:
        vector = self._embed(text)
        if vector is None:
            return False
        with self._Session.begin() as s:  # type: Session
            s.add(VectorRow(
                kind=kind, text=text, ref_id=ref_id, user_id=user_id,
                ticker=ticker, embedding=vector, meta=metadata or {},
            ))
        return True

    def search(
        self,
        query: str,
        *,
        k: int = 5,
        user_id: Optional[str] = None,
        kind: Optional[str] = None,
        ticker: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[MemoryHit]:
        qvec = self._embed(query)
        if qvec is None:
            return []

        stmt = select(VectorRow)
        if user_id is not None:
            stmt = stmt.where(VectorRow.user_id == user_id)
        if kind is not None:
            stmt = stmt.where(VectorRow.kind == kind)
        if ticker is not None:
            stmt = stmt.where(VectorRow.ticker == ticker)

        with self._Session() as s:  # type: Session
            rows = s.execute(stmt).scalars().all()

        scored = [
            MemoryHit(
                kind=row.kind, ref_id=row.ref_id, text=row.text,
                score=cosine(qvec, row.embedding or []),
                ticker=row.ticker, user_id=row.user_id, metadata=row.meta or {},
            )
            for row in rows
        ]
        scored = [h for h in scored if h.score > min_score]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:k]
