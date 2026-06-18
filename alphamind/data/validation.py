"""Financial Validation Layer.

Four kinds of checks, all pure and deterministic:
  • unit       — values are the right kind (currency vs ratio vs percent).
  • currency   — currency is known and consistent (INR for *.NS/*.BO, else a 3-letter code).
  • range      — each metric falls in a plausible band (rejects unit errors / typos).
  • cross-field — internal consistency (P/E ≈ market_cap/net_income, FCF ≤ OCF, …).

`validate_metrics` returns a list of issues; `quality.py` turns those into
per-field confidence and the fail-safe "Data unavailable" decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .schemas import FIELD_UNITS

# Plausible absolute ranges (currency values are unit-agnostic — we only catch
# gross errors like negatives or astronomically large numbers).
_RANGES = {
    "price": (0.0, 1e7),
    "revenue": (0.0, 1e15),
    "market_cap": (0.0, 1e16),
    "ebitda": (-1e14, 1e15),
    "operating_cash_flow": (-1e14, 1e15),
    "free_cash_flow": (-1e14, 1e15),
    "enterprise_value": (0.0, 1e16),
    "net_income": (-1e14, 1e14),
    "eps": (-1e4, 1e4),
    "pe_ratio": (-5000.0, 5000.0),
    "roe": (-5.0, 5.0),    # -500%..500%
    "roce": (-5.0, 5.0),
}

# Relative tolerance for cross-field identities (data is reported at different
# fiscal dates across providers, so identities are approximate).
_CROSS_TOL = 0.25


@dataclass
class ValidationIssue:
    field: str
    severity: str  # "error" | "warning"
    message: str


def _num(metrics, field) -> Optional[float]:
    v = getattr(metrics, field, None)
    return v if isinstance(v, (int, float)) else None


def validate_currency(metrics, ticker: str) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    cur = (metrics.currency or "").upper()
    is_indian = ticker.upper().endswith((".NS", ".BO"))
    if not cur:
        issues.append(ValidationIssue("currency", "warning", "currency not reported"))
    elif is_indian and cur != "INR":
        issues.append(ValidationIssue("currency", "error", f"Indian ticker should be INR, got {cur}"))
    elif len(cur) != 3 and " " not in cur:
        issues.append(ValidationIssue("currency", "warning", f"unexpected currency code '{cur}'"))
    return issues


def validate_ranges(metrics) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    for field, (lo, hi) in _RANGES.items():
        v = _num(metrics, field)
        if v is None:
            continue
        if v < lo or v > hi:
            issues.append(ValidationIssue(field, "error", f"{field}={v:g} outside plausible range [{lo:g}, {hi:g}]"))
    return issues


def validate_units(metrics) -> List[ValidationIssue]:
    """Catch obvious unit errors: percentages given as whole numbers, etc."""
    issues: List[ValidationIssue] = []
    for field in ("roe", "roce"):
        v = _num(metrics, field)
        if v is not None and abs(v) > 5:  # >500% almost certainly means 15 meant 0.15
            issues.append(ValidationIssue(field, "warning", f"{field}={v:g} looks like a percent not a fraction"))
    return issues


def validate_cross_field(metrics) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    mcap = _num(metrics, "market_cap")
    ni = _num(metrics, "net_income")
    pe = _num(metrics, "pe_ratio")
    price = _num(metrics, "price")
    eps = _num(metrics, "eps")
    ocf = _num(metrics, "operating_cash_flow")
    fcf = _num(metrics, "free_cash_flow")
    ev = _num(metrics, "enterprise_value")

    # P/E ≈ market_cap / net_income (when profitable)
    if pe is not None and mcap and ni and ni > 0:
        implied = mcap / ni
        if implied and abs(pe - implied) / abs(implied) > _CROSS_TOL:
            issues.append(ValidationIssue("pe_ratio", "warning",
                f"P/E {pe:.1f} disagrees with market_cap/net_income {implied:.1f}"))

    # P/E ≈ price / eps
    if pe is not None and price and eps and eps > 0:
        implied = price / eps
        if abs(pe - implied) / abs(implied) > _CROSS_TOL:
            issues.append(ValidationIssue("pe_ratio", "warning",
                f"P/E {pe:.1f} disagrees with price/eps {implied:.1f}"))

    # FCF should not exceed OCF (capex is an outflow)
    if fcf is not None and ocf is not None and fcf > ocf * (1 + _CROSS_TOL):
        issues.append(ValidationIssue("free_cash_flow", "warning",
            f"FCF {fcf:g} exceeds operating cash flow {ocf:g}"))

    # Enterprise value should be roughly ≥ market cap only loosely; flag if << market cap
    if ev is not None and mcap and ev < mcap * 0.3:
        issues.append(ValidationIssue("enterprise_value", "warning",
            f"enterprise_value {ev:g} far below market_cap {mcap:g}"))

    return issues


def validate_metrics(metrics, ticker: str) -> List[ValidationIssue]:
    """Run all four validation layers and return the combined issues."""
    return (
        validate_currency(metrics, ticker)
        + validate_ranges(metrics)
        + validate_units(metrics)
        + validate_cross_field(metrics)
    )


def unit_of(field: str) -> str:
    return FIELD_UNITS.get(field, "currency")
