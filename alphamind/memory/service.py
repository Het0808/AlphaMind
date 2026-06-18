"""MemoryService — the single facade over all persistent memory.

Wraps the four structured stores (user / company / research / conversation) and
the vector memory, and exposes `recall()` which runs the hybrid retrieval strategy.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from .db import get_engine, init_db
from .models import CompanyRow, MessageRow, ResearchRow, UserRow
from .retrieval import recall as _recall
from .schemas import (
    CompanyMemory,
    ConversationMessage,
    MemoryContext,
    ResearchRecord,
    UserProfile,
)
from .vector import VectorMemory

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, engine: Optional[Engine] = None, embedder: object | None = None):
        if engine is None:
            self.engine = get_engine()  # get_engine() already runs init_db
        else:
            self.engine = engine
            init_db(self.engine)  # ensure tables exist for an injected engine
        self._Session = sessionmaker(self.engine, expire_on_commit=False, future=True)
        self._embedder = embedder
        self.vector = VectorMemory(self._Session, self._get_embedder)

    def _get_embedder(self):
        if self._embedder is None:
            from ..rag.embeddings import get_embeddings  # lazy: avoids OpenAI import at startup

            self._embedder = get_embeddings()
        return self._embedder

    # ── User profile memory ────────────────────────────────────────────
    def upsert_user_profile(
        self, user_id: str, *, name: Optional[str] = None,
        risk_tolerance: Optional[str] = None, preferences: Optional[Dict[str, Any]] = None,
    ) -> UserProfile:
        with self._Session.begin() as s:
            row = s.get(UserRow, user_id) or UserRow(id=user_id, preferences={})
            if name is not None:
                row.name = name
            if risk_tolerance is not None:
                row.risk_tolerance = risk_tolerance
            if preferences is not None:
                row.preferences = {**(row.preferences or {}), **preferences}
            s.add(row)
            s.flush()
            return UserProfile.model_validate(row)

    def get_user_profile(self, user_id: Optional[str]) -> Optional[UserProfile]:
        if not user_id:
            return None
        with self._Session() as s:
            row = s.get(UserRow, user_id)
            return UserProfile.model_validate(row) if row else None

    # ── Company memory ─────────────────────────────────────────────────
    def upsert_company_memory(
        self, ticker: str, *, name: Optional[str] = None,
        sector: Optional[str] = None, notes: Optional[Dict[str, Any]] = None,
    ) -> CompanyMemory:
        ticker = ticker.upper()
        with self._Session.begin() as s:
            row = s.get(CompanyRow, ticker) or CompanyRow(ticker=ticker, notes={})
            if name is not None:
                row.name = name
            if sector is not None:
                row.sector = sector
            if notes is not None:
                row.notes = {**(row.notes or {}), **notes}
            s.add(row)
            s.flush()
            mem = CompanyMemory.model_validate(row)
        summary = (notes or {}).get("summary") if notes else None
        if summary:
            self.vector.add(kind="company", text=f"{ticker} {name or ''}: {summary}",
                            ref_id=ticker, ticker=ticker, metadata={"name": name})
        return mem

    def get_company_memory(self, ticker: Optional[str]) -> Optional[CompanyMemory]:
        if not ticker:
            return None
        with self._Session() as s:
            row = s.get(CompanyRow, ticker.upper())
            return CompanyMemory.model_validate(row) if row else None

    # ── Research history ───────────────────────────────────────────────
    def add_research_record(
        self, *, ticker: str, summary: str, recommendation: Optional[str] = None,
        user_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None,
    ) -> ResearchRecord:
        ticker = ticker.upper()
        with self._Session.begin() as s:
            row = ResearchRow(
                user_id=user_id, ticker=ticker, summary=summary,
                recommendation=recommendation, payload=payload or {},
            )
            s.add(row)
            s.flush()
            record = ResearchRecord.model_validate(row)
        self.vector.add(
            kind="research", text=f"{ticker}: {summary}", ref_id=str(record.id),
            user_id=user_id, ticker=ticker, metadata={"recommendation": recommendation},
        )
        return record

    def get_research_history(
        self, *, user_id: Optional[str] = None, ticker: Optional[str] = None, limit: int = 10,
    ) -> List[ResearchRecord]:
        stmt = select(ResearchRow).order_by(desc(ResearchRow.created_at)).limit(limit)
        if user_id is not None:
            stmt = stmt.where(ResearchRow.user_id == user_id)
        if ticker is not None:
            stmt = stmt.where(ResearchRow.ticker == ticker.upper())
        with self._Session() as s:
            return [ResearchRecord.model_validate(r) for r in s.execute(stmt).scalars().all()]

    # ── Conversation history ───────────────────────────────────────────
    def add_message(
        self, *, thread_id: str, role: str, content: str, user_id: Optional[str] = None,
    ) -> ConversationMessage:
        with self._Session.begin() as s:
            row = MessageRow(thread_id=thread_id, user_id=user_id, role=role, content=content)
            s.add(row)
            s.flush()
            return ConversationMessage.model_validate(row)

    def get_conversation(self, thread_id: str, *, limit: int = 50) -> List[ConversationMessage]:
        stmt = (
            select(MessageRow)
            .where(MessageRow.thread_id == thread_id)
            .order_by(MessageRow.created_at)
            .limit(limit)
        )
        with self._Session() as s:
            return [ConversationMessage.model_validate(r) for r in s.execute(stmt).scalars().all()]

    # ── Hybrid recall ──────────────────────────────────────────────────
    def recall(
        self, query: str, *, user_id: Optional[str] = None,
        ticker: Optional[str] = None, k: Optional[int] = None,
        company_scoped: bool = False,
    ) -> MemoryContext:
        return _recall(self, query, user_id=user_id, ticker=ticker, k=k, company_scoped=company_scoped)


def get_memory_service() -> MemoryService:
    """Build a MemoryService from configuration (engine resolved from settings)."""
    return MemoryService()
