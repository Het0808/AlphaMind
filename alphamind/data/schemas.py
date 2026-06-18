"""Validated, structured financial-data contracts.

These are the canonical shapes the service returns for *any* public ticker,
independent of which provider supplied each field. Pydantic enforces types and
rejects non-finite numbers (NaN/inf) that providers occasionally emit.
"""

from __future__ import annotations

import math
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,14}$")  # allows Indian symbols e.g. RELIANCE.NS, TATAMOTORS.NS

# Canonical field sets — shared by providers and the merge logic.
OVERVIEW_FIELDS = [
    "name", "sector", "industry", "description",
    "exchange", "currency", "country", "website", "employees",
]
METRIC_FIELDS = [
    "price", "revenue", "net_income", "eps", "market_cap", "pe_ratio",
    "ebitda", "operating_cash_flow", "free_cash_flow", "enterprise_value",
    "roe", "roce", "fiscal_period", "currency",
]

# Numeric metric fields — used to treat NaN/inf as *absent* during merging so a
# garbage value from one provider doesn't block backfill from another.
NUMERIC_METRIC_FIELDS = {
    "price", "revenue", "net_income", "eps", "market_cap", "pe_ratio",
    "ebitda", "operating_cash_flow", "free_cash_flow", "enterprise_value",
    "roe", "roce",
}

# Semantic unit per field — drives validation, conversion and which values must
# NOT be currency-converted (ratios / per-share / percentages).
FIELD_UNITS = {
    "price": "currency", "revenue": "currency", "net_income": "currency",
    "market_cap": "currency", "ebitda": "currency", "operating_cash_flow": "currency",
    "free_cash_flow": "currency", "enterprise_value": "currency",
    "eps": "per_share", "pe_ratio": "ratio", "roe": "percent", "roce": "percent",
}
# Monetary fields are the only ones eligible for currency conversion.
MONETARY_FIELDS = {f for f, u in FIELD_UNITS.items() if u == "currency"}


def clean_field(field: str, value):
    """Return the merge-ready value for a field, or None if it should be skipped."""
    if field in NUMERIC_METRIC_FIELDS:
        return to_finite_float(value)
    return value


def to_finite_float(value) -> Optional[float]:
    """Coerce to float, returning None for missing / non-numeric / NaN / inf."""
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if (math.isnan(f) or math.isinf(f)) else f


def normalize_ticker(ticker: str) -> str:
    return (ticker or "").strip().upper()


def is_valid_ticker(ticker: str) -> bool:
    return bool(TICKER_RE.match(normalize_ticker(ticker)))


class CompanyOverview(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    exchange: Optional[str] = None
    currency: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    employees: Optional[int] = None

    @field_validator("ticker")
    @classmethod
    def _upper(cls, v: str) -> str:
        return normalize_ticker(v)

    @field_validator("employees", mode="before")
    @classmethod
    def _int_or_none(cls, v):
        f = to_finite_float(v)
        return int(f) if f is not None else None


class FinancialMetrics(BaseModel):
    """Core, comparable metrics for any public company (latest annual where applicable)."""

    model_config = ConfigDict(extra="ignore")

    ticker: str
    price: Optional[float] = None
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    eps: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    ebitda: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    free_cash_flow: Optional[float] = None
    enterprise_value: Optional[float] = None
    roe: Optional[float] = None   # return on equity (fraction, e.g. 0.15)
    roce: Optional[float] = None  # return on capital employed (fraction)
    fiscal_period: Optional[str] = None
    currency: Optional[str] = None

    @field_validator("ticker")
    @classmethod
    def _upper(cls, v: str) -> str:
        return normalize_ticker(v)

    @field_validator(
        "price", "revenue", "net_income", "eps", "market_cap", "pe_ratio",
        "ebitda", "operating_cash_flow", "free_cash_flow", "enterprise_value",
        "roe", "roce",
        mode="before",
    )
    @classmethod
    def _finite(cls, v):
        return to_finite_float(v)


class FieldQuality(BaseModel):
    """Quality record for a single metric: provenance, agreement, confidence."""

    field: str
    value: Optional[float] = None
    unit: str = "currency"            # currency | per_share | ratio | percent
    currency: Optional[str] = None
    sources: Dict[str, float] = {}    # provider -> the value it reported
    periods: Dict[str, str] = {}      # provider -> reporting period bucket (ttm | annual | unknown)
    chosen_source: Optional[str] = None
    agreement: Optional[float] = None  # 0..1 cross-source agreement among SAME-period values
    confidence: float = 0.0            # 0..1
    status: str = "unavailable"        # ok | single_source | disagreement | out_of_range | unavailable
    issues: List[str] = []


class QualityReport(BaseModel):
    """Per-snapshot data-quality summary for the Data Quality Dashboard."""

    overall_confidence: float = 0.0
    providers: List[str] = []
    field_quality: Dict[str, FieldQuality] = {}
    validations: List[str] = []        # cross-field / range validation messages
    last_updated: str = ""


class FinancialSnapshot(BaseModel):
    """Everything the service returns for one ticker, with full provenance + quality."""

    ticker: str
    overview: CompanyOverview
    metrics: FinancialMetrics
    providers_used: List[str] = []
    field_sources: Dict[str, str] = {}
    warnings: List[str] = []
    quality: Optional[QualityReport] = None
    retrieved_at: str = ""

    @field_validator("retrieved_at")
    @classmethod
    def _default_ts(cls, v: str) -> str:
        return v or datetime.now(timezone.utc).isoformat()
