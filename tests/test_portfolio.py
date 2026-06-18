"""Offline tests for the Portfolio Advisor (deterministic engine, no LLM)."""

import pytest

from alphamind.portfolio.advisor import advise
from alphamind.portfolio.analytics import (
    analyze_diversification,
    analyze_risk,
    analyze_sectors,
    effective_limits,
    normalize_holdings,
    recommend_positions,
)
from alphamind.portfolio.schemas import (
    Holding,
    PortfolioInput,
    PositionAction,
    RiskProfile,
    RiskTolerance,
)


def _profile(tol=RiskTolerance.BALANCED, **kw):
    return RiskProfile(risk_tolerance=tol, **kw)


def test_weight_normalization_from_values():
    holds = [Holding(ticker="A", value=30), Holding(ticker="B", value=10)]
    norm = normalize_holdings(holds)
    assert abs(norm[0].weight - 0.75) < 1e-6 and abs(norm[1].weight - 0.25) < 1e-6


def test_equal_weight_when_unspecified():
    norm = normalize_holdings([Holding(ticker="A"), Holding(ticker="B"), Holding(ticker="C")])
    assert all(abs(x.weight - 1 / 3) < 1e-6 for x in norm)


def test_diversification_hhi_and_level():
    limits = effective_limits(_profile())
    concentrated = normalize_holdings([Holding(ticker="A", weight=0.8), Holding(ticker="B", weight=0.2)])
    div = analyze_diversification(concentrated, limits)
    assert div.concentration_level == "HIGH"
    assert div.top_position_ticker == "A"
    assert pytest.approx(div.hhi, abs=1e-3) == 0.68  # 0.8^2 + 0.2^2

    spread = normalize_holdings([Holding(ticker=str(i), weight=1) for i in range(12)])
    assert analyze_diversification(spread, limits).concentration_level == "LOW"


def test_sector_overweight_detection():
    limits = effective_limits(_profile())  # max_sector 0.40
    holds = [
        Holding(ticker="A", weight=0.3, sector="Tech"),
        Holding(ticker="B", weight=0.3, sector="Tech"),
        Holding(ticker="C", weight=0.4, sector="Energy"),
    ]
    sectors = analyze_sectors(normalize_holdings(holds), limits)
    assert "Tech" in sectors.overweight_sectors  # 0.6 > 0.40
    assert sectors.top_sector == "Tech"


def test_risk_alignment_over_for_conservative():
    limits = effective_limits(_profile(RiskTolerance.CONSERVATIVE))  # ceiling 4
    holds = [Holding(ticker="A", weight=1.0, risk_score=8)]
    risk = analyze_risk(normalize_holdings(holds), limits)
    assert risk.alignment == "OVER"
    assert risk.weighted_risk_score == 8.0


def test_recommend_sell_is_avoided_and_overweight_reduced():
    limits = effective_limits(_profile())  # max_pos 0.25
    holds = [
        Holding(ticker="BAD", weight=0.1, sector="X", recommendation="STRONG_SELL"),
        Holding(ticker="BIG", weight=0.5, sector="Y", recommendation="HOLD"),
        Holding(ticker="GEM", weight=0.1, sector="Z", recommendation="BUY", conviction=9, risk_score=4),
        Holding(ticker="MEH", weight=0.3, sector="W", recommendation="HOLD"),
    ]
    norm = normalize_holdings(holds)
    sectors = analyze_sectors(norm, limits)
    recs = {r.ticker: r for r in recommend_positions(norm, limits, sectors)}

    assert recs["BAD"].action == PositionAction.AVOID
    assert recs["BAD"].target_weight == 0.0
    assert recs["BIG"].action == PositionAction.REDUCE   # 50% > 25% cap
    assert recs["BIG"].target_weight < recs["BIG"].current_weight
    assert recs["GEM"].action == PositionAction.BUY      # buy-rated, high conviction, room
    assert recs["MEH"].action == PositionAction.REDUCE   # 30% > 25% cap


def test_advise_end_to_end_deterministic():
    req = PortfolioInput(
        risk_profile=_profile(RiskTolerance.BALANCED, target_return=0.08),
        holdings=[
            Holding(ticker="NVDA", weight=0.4, sector="Tech", recommendation="BUY", conviction=8, risk_score=6),
            Holding(ticker="AAPL", weight=0.3, sector="Tech", recommendation="HOLD", conviction=6, risk_score=4),
            Holding(ticker="XOM", weight=0.3, sector="Energy", recommendation="SELL", conviction=6, risk_score=7),
        ],
    )
    advice = advise(req, use_llm=False)

    assert {p.ticker for p in advice.positions} == {"NVDA", "AAPL", "XOM"}
    assert "Tech" in advice.sector_exposure.overweight_sectors  # 0.7 > 0.40
    assert advice.expected_returns.meets_target is not None
    assert advice.overall_assessment
    # Every position has a concrete action and reasoning.
    for p in advice.positions:
        assert p.action in PositionAction
        assert p.reasoning
    # Sell-rated + overweight Tech should trigger rebalancing actions.
    assert advice.rebalancing_actions
