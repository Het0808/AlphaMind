"""Pydantic contracts for memory records and the assembled recall context.

`from_attributes=True` lets these validate straight from SQLAlchemy ORM rows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

_ORM = ConfigDict(from_attributes=True)


class UserProfile(BaseModel):
    model_config = _ORM
    id: str
    name: Optional[str] = None
    risk_tolerance: Optional[str] = None  # e.g. conservative / balanced / aggressive
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CompanyMemory(BaseModel):
    model_config = _ORM
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    notes: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[datetime] = None


class ResearchRecord(BaseModel):
    model_config = _ORM
    id: Optional[int] = None
    user_id: Optional[str] = None
    ticker: str
    summary: str
    recommendation: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class ConversationMessage(BaseModel):
    model_config = _ORM
    id: Optional[int] = None
    thread_id: str
    user_id: Optional[str] = None
    role: str  # "user" | "assistant" | "system"
    content: str
    created_at: Optional[datetime] = None


class MemoryHit(BaseModel):
    """A semantically retrieved memory with its similarity score."""

    kind: str  # "research" | "company" | "message"
    ref_id: Optional[str] = None
    text: str
    score: float
    ticker: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemoryContext(BaseModel):
    """The result of a recall: everything relevant to ground the next turn."""

    query: str
    user_profile: Optional[UserProfile] = None
    companies: List[CompanyMemory] = Field(default_factory=list)
    recent_research: List[ResearchRecord] = Field(default_factory=list)
    semantic_hits: List[MemoryHit] = Field(default_factory=list)

    def has_content(self) -> bool:
        return bool(self.user_profile or self.companies or self.recent_research or self.semantic_hits)

    def format(self, *, max_hits: int = 5) -> str:
        """Render a compact, prompt-injectable context block."""
        lines: List[str] = []
        if self.user_profile:
            p = self.user_profile
            bits = [b for b in (p.name, p.risk_tolerance and f"{p.risk_tolerance} risk") if b]
            if p.preferences:
                bits.append("prefs=" + ", ".join(f"{k}:{v}" for k, v in p.preferences.items()))
            if bits:
                lines.append("User profile: " + "; ".join(bits))

        for c in self.companies:
            note = c.notes.get("summary") if isinstance(c.notes, dict) else None
            lines.append(f"Known company {c.ticker} ({c.name or '?'}): {note or 'previously analyzed'}")

        if self.recent_research:
            tickers = ", ".join(dict.fromkeys(r.ticker for r in self.recent_research))
            lines.append(f"Recently analyzed: {tickers}")

        for hit in self.semantic_hits[:max_hits]:
            tag = f"{hit.kind}:{hit.ticker}" if hit.ticker else hit.kind
            lines.append(f"[recall {tag} • sim {hit.score:.2f}] {hit.text[:280]}")

        return "\n".join(lines)
