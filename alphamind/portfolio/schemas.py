"""Contracts for the Portfolio Advisor: inputs, analyses, and recommendations."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..schemas import Recommendation, RiskLevel


class RiskTolerance(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    BALANCED = "BALANCED"
    AGGRESSIVE = "AGGRESSIVE"


class PositionAction(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    REDUCE = "REDUCE"
    AVOID = "AVOID"


# ── Inputs ──────────────────────────────────────────────────────────────────
class RiskProfile(BaseModel):
    risk_tolerance: RiskTolerance = RiskTolerance.BALANCED
    horizon_years: float = 5.0
    target_return: Optional[float] = Field(None, description="Desired annual return, e.g. 0.08.")
    # Optional explicit limits; otherwise defaulted from the tolerance band.
    max_position_weight: Optional[float] = Field(None, description="Max weight for a single holding (0-1).")
    max_sector_weight: Optional[float] = Field(None, description="Max weight for a single sector (0-1).")
    objectives: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)


class Holding(BaseModel):
    ticker: str
    name: Optional[str] = None
    sector: str = "Unknown"
    weight: Optional[float] = Field(None, description="Portfolio weight (0-1). Derived from value if omitted.")
    value: Optional[float] = Field(None, description="Position market value (used if weight omitted).")
    recommendation: Optional[Recommendation] = None
    conviction: Optional[int] = Field(None, ge=1, le=10)
    risk_score: Optional[int] = Field(None, ge=1, le=10)
    beta: Optional[float] = None
    expected_return: Optional[float] = Field(None, description="Annual expected return, e.g. 0.12.")


class PortfolioInput(BaseModel):
    risk_profile: RiskProfile = Field(default_factory=RiskProfile)
    holdings: List[Holding]


# ── Analyses ────────────────────────────────────────────────────────────────
class DiversificationAnalysis(BaseModel):
    n_holdings: int
    hhi: float = Field(..., description="Herfindahl-Hirschman concentration index (sum of weights squared).")
    effective_holdings: float = Field(..., description="1 / HHI — effective number of equally-weighted positions.")
    top_position_ticker: Optional[str] = None
    top_position_weight: float = 0.0
    concentration_level: str = "MODERATE"  # LOW | MODERATE | HIGH
    score: float = Field(..., description="Diversification quality, 0-1.")
    notes: List[str] = Field(default_factory=list)


class SectorExposure(BaseModel):
    weights: Dict[str, float] = Field(default_factory=dict)
    n_sectors: int = 0
    top_sector: Optional[str] = None
    top_sector_weight: float = 0.0
    overweight_sectors: List[str] = Field(default_factory=list)
    score: float = 0.0
    notes: List[str] = Field(default_factory=list)


class PortfolioRiskAnalysis(BaseModel):
    weighted_risk_score: float = Field(..., description="Weighted 1-10 risk score.")
    weighted_beta: float
    risk_level: RiskLevel
    alignment: str = Field(..., description="UNDER | ALIGNED | OVER relative to the risk profile.")
    score: float
    notes: List[str] = Field(default_factory=list)


class ExpectedReturns(BaseModel):
    weighted_expected_return: float
    risk_adjusted_return: float
    meets_target: Optional[bool] = None
    notes: List[str] = Field(default_factory=list)


# ── Output ──────────────────────────────────────────────────────────────────
class PositionRecommendation(BaseModel):
    ticker: str
    name: Optional[str] = None
    action: PositionAction
    current_weight: float
    target_weight: float
    reasoning: str
    factors: List[str] = Field(default_factory=list)


class PortfolioAdvice(BaseModel):
    risk_profile: RiskProfile
    diversification: DiversificationAnalysis
    sector_exposure: SectorExposure
    portfolio_risk: PortfolioRiskAnalysis
    expected_returns: ExpectedReturns
    positions: List[PositionRecommendation]
    overall_assessment: str
    rebalancing_actions: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
