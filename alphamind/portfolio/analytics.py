"""Deterministic portfolio analytics and the per-position recommendation engine.

No LLM here — everything is explainable math so results are reproducible and
unit-testable. The advisor layers an optional narrative on top of these outputs.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

from ..schemas import Recommendation, RiskLevel
from .schemas import (
    DiversificationAnalysis,
    ExpectedReturns,
    Holding,
    PortfolioRiskAnalysis,
    PositionAction,
    PositionRecommendation,
    RiskProfile,
    RiskTolerance,
    SectorExposure,
)

# Tolerance-band defaults: position/sector caps, acceptable risk window, target return.
_BANDS = {
    RiskTolerance.CONSERVATIVE: dict(max_pos=0.15, max_sector=0.30, risk_floor=2.0, risk_ceiling=4.0, target=0.05),
    RiskTolerance.BALANCED: dict(max_pos=0.25, max_sector=0.40, risk_floor=4.0, risk_ceiling=6.0, target=0.08),
    RiskTolerance.AGGRESSIVE: dict(max_pos=0.35, max_sector=0.55, risk_floor=5.0, risk_ceiling=8.0, target=0.12),
}

# Base annual expected return by analyst recommendation.
_ER_BASE = {
    Recommendation.STRONG_BUY: 0.16, Recommendation.BUY: 0.10, Recommendation.HOLD: 0.05,
    Recommendation.SELL: -0.03, Recommendation.STRONG_SELL: -0.10,
}


@dataclass
class Limits:
    max_pos: float
    max_sector: float
    risk_floor: float
    risk_ceiling: float
    target: float


def effective_limits(profile: RiskProfile) -> Limits:
    band = _BANDS[profile.risk_tolerance]
    return Limits(
        max_pos=profile.max_position_weight if profile.max_position_weight is not None else band["max_pos"],
        max_sector=profile.max_sector_weight if profile.max_sector_weight is not None else band["max_sector"],
        risk_floor=band["risk_floor"],
        risk_ceiling=band["risk_ceiling"],
        target=profile.target_return if profile.target_return is not None else band["target"],
    )


@dataclass
class Normalized:
    h: Holding
    weight: float
    risk: float
    beta: float
    er: float


def _expected_return(h: Holding) -> float:
    if h.expected_return is not None:
        return h.expected_return
    base = _ER_BASE.get(h.recommendation, 0.05)
    conv = h.conviction if h.conviction is not None else 5
    # Tilt the base by conviction (±~40% around the midpoint).
    return round(base * (0.6 + 0.08 * conv), 4)


def normalize_holdings(holdings: List[Holding]) -> List[Normalized]:
    """Resolve each holding's weight (from weight/value/equal) and key inputs."""
    explicit = [h.weight for h in holdings if h.weight is not None]
    values = [h.value for h in holdings if h.value is not None]

    if explicit and len(explicit) == len(holdings):
        total = sum(explicit) or 1.0
        weights = [(h.weight or 0) / total for h in holdings]
    elif values and len(values) == len(holdings):
        total = sum(values) or 1.0
        weights = [(h.value or 0) / total for h in holdings]
    else:
        weights = [1.0 / len(holdings)] * len(holdings) if holdings else []

    out = []
    for h, w in zip(holdings, weights):
        out.append(Normalized(
            h=h, weight=round(w, 6),
            risk=float(h.risk_score) if h.risk_score is not None else 5.0,
            beta=h.beta if h.beta is not None else 1.0,
            er=_expected_return(h),
        ))
    return out


# ── Analyses ────────────────────────────────────────────────────────────────
def analyze_diversification(norm: List[Normalized], limits: Limits) -> DiversificationAnalysis:
    n = len(norm)
    hhi = sum(x.weight ** 2 for x in norm)
    eff = (1.0 / hhi) if hhi > 0 else 0.0
    top = max(norm, key=lambda x: x.weight) if norm else None

    if eff >= 10:
        level = "LOW"
    elif eff >= 5:
        level = "MODERATE"
    else:
        level = "HIGH"

    score = max(0.0, min(1.0, eff / 10.0))
    notes = []
    if top and top.weight > limits.max_pos:
        notes.append(f"{top.h.ticker} is {top.weight:.0%}, above the {limits.max_pos:.0%} single-position cap.")
        score *= 0.8
    if n < 5:
        notes.append("Fewer than 5 holdings — limited idiosyncratic diversification.")

    return DiversificationAnalysis(
        n_holdings=n, hhi=round(hhi, 4), effective_holdings=round(eff, 2),
        top_position_ticker=top.h.ticker if top else None,
        top_position_weight=round(top.weight, 4) if top else 0.0,
        concentration_level=level, score=round(score, 3), notes=notes,
    )


def analyze_sectors(norm: List[Normalized], limits: Limits) -> SectorExposure:
    weights: Dict[str, float] = defaultdict(float)
    for x in norm:
        weights[x.h.sector] += x.weight
    weights = {k: round(v, 4) for k, v in weights.items()}

    overweight = [s for s, w in weights.items() if w > limits.max_sector]
    top_sector, top_w = (max(weights.items(), key=lambda kv: kv[1]) if weights else (None, 0.0))
    excess = sum(max(0.0, w - limits.max_sector) for w in weights.values())
    score = max(0.0, 1.0 - excess * 2)

    notes = [f"{s} is {weights[s]:.0%}, above the {limits.max_sector:.0%} sector cap." for s in overweight]
    return SectorExposure(
        weights=weights, n_sectors=len(weights), top_sector=top_sector,
        top_sector_weight=round(top_w, 4), overweight_sectors=overweight,
        score=round(score, 3), notes=notes,
    )


def analyze_risk(norm: List[Normalized], limits: Limits) -> PortfolioRiskAnalysis:
    wr = sum(x.weight * x.risk for x in norm)
    wb = sum(x.weight * x.beta for x in norm)

    if wr < 4:
        level = RiskLevel.LOW
    elif wr < 6:
        level = RiskLevel.MODERATE
    elif wr < 7.5:
        level = RiskLevel.ELEVATED
    else:
        level = RiskLevel.HIGH

    if wr > limits.risk_ceiling:
        alignment = "OVER"
    elif wr < limits.risk_floor:
        alignment = "UNDER"
    else:
        alignment = "ALIGNED"

    # Best score when aligned to the middle of the tolerance band.
    mid = (limits.risk_floor + limits.risk_ceiling) / 2
    score = max(0.0, 1.0 - abs(wr - mid) / 5.0)

    notes = []
    if alignment == "OVER":
        notes.append(f"Weighted risk {wr:.1f} exceeds the tolerance ceiling {limits.risk_ceiling:.1f}.")
    elif alignment == "UNDER":
        notes.append(f"Weighted risk {wr:.1f} is below the tolerance floor {limits.risk_floor:.1f} — may be under-invested for the goal.")

    return PortfolioRiskAnalysis(
        weighted_risk_score=round(wr, 2), weighted_beta=round(wb, 2),
        risk_level=level, alignment=alignment, score=round(score, 3), notes=notes,
    )


def analyze_returns(norm: List[Normalized], limits: Limits) -> ExpectedReturns:
    wer = sum(x.weight * x.er for x in norm)
    wr = sum(x.weight * x.risk for x in norm) or 5.0
    risk_adj = wer / max(wr / 5.0, 0.1)  # normalize risk so 5/10 -> 1.0
    meets = wer >= limits.target

    notes = [f"Weighted expected return {wer:.1%} vs target {limits.target:.1%}."]
    if not meets:
        notes.append("Below target — consider higher-conviction or higher-return positions within risk limits.")
    return ExpectedReturns(
        weighted_expected_return=round(wer, 4), risk_adjusted_return=round(risk_adj, 4),
        meets_target=meets, notes=notes,
    )


# ── Per-position recommendations ─────────────────────────────────────────────
def _sector_trim_set(norm: List[Normalized], overweight_sectors: List[str]) -> set:
    """The largest holding in each overweight sector is the trim candidate."""
    trim = set()
    for sector in overweight_sectors:
        members = [x for x in norm if x.h.sector == sector]
        if members:
            trim.add(max(members, key=lambda x: x.weight).h.ticker)
    return trim


def recommend_positions(
    norm: List[Normalized], limits: Limits, sectors: SectorExposure,
) -> List[PositionRecommendation]:
    trim = _sector_trim_set(norm, sectors.overweight_sectors)
    recs: List[PositionRecommendation] = []

    for x in norm:
        h = x.h
        factors: List[str] = []
        avoid = reduce = buy = False

        rec = h.recommendation
        conv = h.conviction if h.conviction is not None else 5

        if rec == Recommendation.STRONG_SELL:
            avoid = True
            factors.append("strong-sell rated")
        elif rec == Recommendation.SELL:
            reduce = True
            factors.append("sell rated")

        if x.weight > limits.max_pos:
            reduce = True
            factors.append(f"overweight ({x.weight:.0%} > {limits.max_pos:.0%} cap)")

        if h.ticker in trim:
            reduce = True
            factors.append(f"largest position in overweight {h.sector} sector")

        if x.risk >= limits.risk_ceiling + 2:
            reduce = True
            factors.append(f"risk {int(x.risk)}/10 high for {limits.risk_ceiling:.0f} ceiling")

        if not (avoid or reduce) and rec in (Recommendation.BUY, Recommendation.STRONG_BUY) \
                and conv >= 7 and x.weight < limits.max_pos * 0.9 and x.risk <= limits.risk_ceiling:
            buy = True
            factors.append(f"buy-rated, conviction {conv}/10, room to add under cap")

        if avoid:
            action, target = PositionAction.AVOID, 0.0
        elif reduce:
            action, target = PositionAction.REDUCE, round(min(x.weight * 0.6, limits.max_pos), 4)
        elif buy:
            target = round(min(limits.max_pos, (x.weight * 1.3) if x.weight > 0 else 0.05), 4)
            action = PositionAction.BUY
        else:
            action, target = PositionAction.HOLD, round(x.weight, 4)
            factors.append("within limits and consistent with the risk profile")

        recs.append(PositionRecommendation(
            ticker=h.ticker, name=h.name, action=action,
            current_weight=round(x.weight, 4), target_weight=target,
            reasoning=_reason(action, factors), factors=factors,
        ))
    return recs


def _reason(action: PositionAction, factors: List[str]) -> str:
    lead = {
        PositionAction.AVOID: "Avoid:",
        PositionAction.REDUCE: "Reduce:",
        PositionAction.BUY: "Add:",
        PositionAction.HOLD: "Hold:",
    }[action]
    return f"{lead} " + "; ".join(factors) + "."
