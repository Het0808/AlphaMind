"""LangGraph shared state.

The graph state is the single object every node reads from and writes to. Each
specialist writes to its OWN dedicated key, which lets the three research
specialists fan out in parallel without write conflicts. `trace` uses an additive
reducer so concurrent nodes can each append a breadcrumb safely.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, List, Optional

from typing_extensions import TypedDict

from .schemas import (
    FinancialReport,
    NewsReport,
    ResearchPlan,
    ResearchReport,
    RiskReport,
    Synthesis,
)


class AgentState(TypedDict, total=False):
    # ── Inputs ──
    ticker: str
    horizon: str
    notes: Optional[str]

    # ── Supervisor ──
    company_name: str
    plan: Optional[ResearchPlan]

    # ── Specialist outputs (each agent owns one key → safe parallel writes) ──
    research_report: Optional[ResearchReport]
    financial_report: Optional[FinancialReport]
    news_report: Optional[NewsReport]
    risk_report: Optional[RiskReport]

    # ── Final synthesis ──
    synthesis: Optional[Synthesis]

    # ── Observability (additive reducer for parallel appends) ──
    trace: Annotated[List[str], add]
