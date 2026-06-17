"""Structured I/O contracts for AlphaMind.

Every agent emits a Pydantic model — never free-form text. These schemas are the
backbone of the platform: they make agent outputs validated, typed, JSON-
serializable, and directly consumable by the API and UI. The LLM is forced into
these shapes via `llm.with_structured_output(Model)`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────
class Recommendation(str, Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class Sentiment(str, Enum):
    VERY_BULLISH = "VERY_BULLISH"
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    VERY_BEARISH = "VERY_BEARISH"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"


# ──────────────────────────────────────────────────────────────────────────
# Request / plan
# ──────────────────────────────────────────────────────────────────────────
class AnalysisRequest(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol, e.g. AAPL.")
    horizon: str = Field("12 months", description="Investment time horizon.")
    notes: Optional[str] = Field(None, description="Optional analyst focus or constraints.")


class ResearchPlan(BaseModel):
    """The supervisor's dispatch plan for the specialist agents."""

    objective: str = Field(..., description="One-sentence research objective.")
    focus_areas: List[str] = Field(..., description="Key questions the team should answer.")
    agents_to_run: List[str] = Field(
        default_factory=lambda: ["research", "financial", "news", "risk"],
        description="Specialist agents the supervisor dispatches.",
    )


# ──────────────────────────────────────────────────────────────────────────
# Specialist agent outputs
# ──────────────────────────────────────────────────────────────────────────
class ResearchReport(BaseModel):
    company_name: str
    sector: str = Field(..., description="Sector / industry.")
    business_summary: str = Field(..., description="What the company does, concisely.")
    moat: str = Field(..., description="Competitive advantage / economic moat.")
    growth_drivers: List[str] = Field(..., description="Primary growth catalysts.")
    competitive_threats: List[str] = Field(..., description="Key competitors / threats.")
    bull_case: str
    bear_case: str


class FinancialReport(BaseModel):
    valuation_summary: str = Field(..., description="Valuation read (cheap/fair/expensive) with rationale.")
    profitability: str = Field(..., description="Margins, returns on capital, quality of earnings.")
    balance_sheet: str = Field(..., description="Leverage, liquidity, solvency assessment.")
    growth_trend: str = Field(..., description="Revenue / earnings growth trajectory.")
    key_metrics: dict = Field(default_factory=dict, description="Raw metrics used (PE, margins, etc.).")
    financial_health_score: int = Field(..., ge=1, le=10, description="1 (weak) .. 10 (strong).")


class NewsItem(BaseModel):
    headline: str
    sentiment: Sentiment
    relevance: str = Field(..., description="Why this matters to the thesis.")


class NewsReport(BaseModel):
    overall_sentiment: Sentiment
    summary: str = Field(..., description="Narrative summary of the current news flow.")
    catalysts: List[str] = Field(..., description="Upcoming or recent catalysts.")
    notable_items: List[NewsItem] = Field(default_factory=list)


class RiskReport(BaseModel):
    overall_risk: RiskLevel
    market_risk: str
    financial_risk: str
    business_risk: str
    red_flags: List[str] = Field(default_factory=list)
    risk_score: int = Field(..., ge=1, le=10, description="1 (low) .. 10 (severe).")


class Synthesis(BaseModel):
    """The supervisor's final judgement, distilled from all specialist reports."""

    recommendation: Recommendation
    conviction: int = Field(..., ge=1, le=10, description="Confidence in the call, 1..10.")
    executive_summary: str
    key_thesis: List[str] = Field(..., description="Top reasons supporting the call.")
    key_risks: List[str] = Field(..., description="Top reasons it could be wrong.")


# ──────────────────────────────────────────────────────────────────────────
# Final aggregated report (API response)
# ──────────────────────────────────────────────────────────────────────────
class InvestmentReport(BaseModel):
    ticker: str
    company_name: str
    horizon: str
    recommendation: Recommendation
    conviction: int = Field(..., ge=1, le=10)
    executive_summary: str
    key_thesis: List[str]
    key_risks: List[str]

    research: ResearchReport
    financials: FinancialReport
    news: NewsReport
    risk: RiskReport

    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    trace: List[str] = Field(default_factory=list, description="Agent execution trace.")
