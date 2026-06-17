"""Typed contracts for the RAG layer, including first-class citations.

Every retrieved chunk carries a `Citation` with the exact filing reference
(ticker, form, accession number, filing date, section and SEC URL) so answers can
always be traced back to the precise source document.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class FilingRef(BaseModel):
    """A pointer to one SEC filing document."""

    ticker: str
    cik: int
    form: str  # e.g. "10-K", "10-Q"
    accession: str  # e.g. "0000320193-24-000123"
    filing_date: str  # YYYY-MM-DD
    period_of_report: Optional[str] = None
    primary_document: str = ""
    url: str = ""


class Citation(BaseModel):
    """An exact, human-readable reference to a source passage."""

    ticker: str
    company: Optional[str] = None
    form: str
    section: str
    accession: str
    filing_date: str
    url: str
    snippet: str = ""
    score: Optional[float] = None

    def reference(self) -> str:
        """Compact citation string, e.g. 'AAPL 10-K filed 2024-11-01 (accession ...), Item 1A Risk Factors'."""
        who = self.company or self.ticker
        return (
            f"{who} {self.form} filed {self.filing_date} "
            f"(accession {self.accession}), {self.section}"
        )


class RetrievedChunk(BaseModel):
    text: str
    score: float
    citation: Citation


class RAGAnswer(BaseModel):
    query: str
    answer: str
    citations: List[Citation] = Field(default_factory=list)
