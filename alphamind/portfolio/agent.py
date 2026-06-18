"""Optional LLM narrative for the Portfolio Advisor.

The actions are decided deterministically (see analytics.py); the LLM only adds a
portfolio-level narrative — an overall assessment and prioritized rebalancing
actions — grounded in the computed analytics. Lazy/graceful: callers fall back to
the deterministic narrative if the LLM is unavailable.
"""

from __future__ import annotations

from typing import List

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..llm import get_llm
from .schemas import (
    DiversificationAnalysis,
    ExpectedReturns,
    PortfolioRiskAnalysis,
    PositionRecommendation,
    RiskProfile,
    SectorExposure,
)

_SYSTEM = (
    "You are AlphaMind's portfolio advisor. Using the user's risk profile and the "
    "computed analytics (diversification, sector exposure, risk, expected returns) "
    "plus the per-position actions, write a concise, decision-grade overall "
    "assessment and a prioritized list of rebalancing actions. Respect the actions "
    "already decided; do not contradict them. Be specific and reference the numbers."
)


class AdvisorNarrative(BaseModel):
    overall_assessment: str = Field(..., description="2-4 sentence portfolio verdict.")
    rebalancing_actions: List[str] = Field(..., description="Prioritized, specific actions.")


def narrate(
    profile: RiskProfile,
    diversification: DiversificationAnalysis,
    sectors: SectorExposure,
    risk: PortfolioRiskAnalysis,
    returns: ExpectedReturns,
    positions: List[PositionRecommendation],
) -> AdvisorNarrative:
    llm = get_llm(temperature=0.1).with_structured_output(AdvisorNarrative)
    actions = "\n".join(f"- {p.ticker}: {p.action.value} — {p.reasoning}" for p in positions)
    return llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=(
            f"Risk profile: {profile.model_dump()}\n\n"
            f"Diversification: {diversification.model_dump()}\n"
            f"Sector exposure: {sectors.model_dump()}\n"
            f"Portfolio risk: {risk.model_dump()}\n"
            f"Expected returns: {returns.model_dump()}\n\n"
            f"Per-position actions:\n{actions}\n\n"
            "Write the assessment and rebalancing actions."
        )),
    ])
