"""PortfolioAdvisorAgent — orchestrates analytics → recommendations → narrative."""

from __future__ import annotations

import logging
from typing import List, Tuple

from ..config import get_settings
from .analytics import (
    analyze_diversification,
    analyze_returns,
    analyze_risk,
    analyze_sectors,
    effective_limits,
    normalize_holdings,
    recommend_positions,
)
from .schemas import PortfolioAdvice, PortfolioInput, PositionAction, PositionRecommendation

logger = logging.getLogger(__name__)


def _deterministic_narrative(
    advice_parts, positions: List[PositionRecommendation],
) -> Tuple[str, List[str]]:
    div, sectors, risk, returns = advice_parts
    counts = {a: sum(1 for p in positions if p.action == a) for a in PositionAction}

    assessment = (
        f"Diversification is {div.concentration_level.lower()} "
        f"({div.effective_holdings:.1f} effective holdings); risk is {risk.risk_level.value.lower()} "
        f"and {risk.alignment.lower()} vs the profile; expected return "
        f"{returns.weighted_expected_return:.1%} "
        f"({'meets' if returns.meets_target else 'is below'} target). "
    )
    if sectors.overweight_sectors:
        assessment += f"Sector concentration in {', '.join(sectors.overweight_sectors)} is a flag. "
    assessment += (
        f"Actions: {counts[PositionAction.BUY]} buy, {counts[PositionAction.HOLD]} hold, "
        f"{counts[PositionAction.REDUCE]} reduce, {counts[PositionAction.AVOID]} avoid."
    )

    actions = [
        f"{p.action.value} {p.ticker} → target {p.target_weight:.0%} ({p.reasoning})"
        for p in positions if p.action != PositionAction.HOLD
    ]
    return assessment, actions


class PortfolioAdvisorAgent:
    def advise(self, request: PortfolioInput, *, use_llm: bool = True) -> PortfolioAdvice:
        limits = effective_limits(request.risk_profile)
        norm = normalize_holdings(request.holdings)

        diversification = analyze_diversification(norm, limits)
        sectors = analyze_sectors(norm, limits)
        risk = analyze_risk(norm, limits)
        returns = analyze_returns(norm, limits)
        positions = recommend_positions(norm, limits, sectors)

        assessment, rebalancing = _deterministic_narrative((diversification, sectors, risk, returns), positions)

        if use_llm and get_settings().is_configured:
            try:
                from .agent import narrate

                narrative = narrate(request.risk_profile, diversification, sectors, risk, returns, positions)
                assessment, rebalancing = narrative.overall_assessment, narrative.rebalancing_actions
            except Exception as exc:  # noqa: BLE001 - fall back to deterministic narrative
                logger.warning("LLM narrative failed; using deterministic: %s", exc)

        return PortfolioAdvice(
            risk_profile=request.risk_profile,
            diversification=diversification,
            sector_exposure=sectors,
            portfolio_risk=risk,
            expected_returns=returns,
            positions=positions,
            overall_assessment=assessment,
            rebalancing_actions=rebalancing,
        )


def advise(request: PortfolioInput, *, use_llm: bool = True) -> PortfolioAdvice:
    return PortfolioAdvisorAgent().advise(request, use_llm=use_llm)
