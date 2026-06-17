"""Market & fundamental data tools.

Backed by yfinance, but every call degrades gracefully: if the network or the
provider is unavailable the agent still receives a well-formed dict (with an
`error` field) instead of raising. This keeps the graph resilient — the LLM can
reason about "data unavailable" rather than crashing the run.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _ticker(symbol: str):
    import yfinance as yf  # imported lazily so the package imports without it

    return yf.Ticker(symbol)


def get_company_profile(symbol: str) -> Dict[str, Any]:
    """Return a qualitative company profile for the research agent."""
    try:
        info = _ticker(symbol).info or {}
        return {
            "ticker": symbol.upper(),
            "company_name": info.get("longName") or info.get("shortName") or symbol.upper(),
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "country": info.get("country", "Unknown"),
            "employees": info.get("fullTimeEmployees"),
            "website": info.get("website"),
            "summary": info.get("longBusinessSummary", "No description available."),
        }
    except Exception as exc:  # noqa: BLE001 - resilience by design
        logger.warning("get_company_profile(%s) failed: %s", symbol, exc)
        return {
            "ticker": symbol.upper(),
            "company_name": symbol.upper(),
            "error": str(exc),
            "summary": "Live profile data unavailable; reason from general knowledge.",
        }


def get_financial_metrics(symbol: str) -> Dict[str, Any]:
    """Return key valuation / profitability / balance-sheet metrics."""
    try:
        info = _ticker(symbol).info or {}
        return {
            "ticker": symbol.upper(),
            "price": info.get("currentPrice"),
            "market_cap": info.get("marketCap"),
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "peg_ratio": info.get("pegRatio"),
            "price_to_book": info.get("priceToBook"),
            "gross_margin": info.get("grossMargins"),
            "operating_margin": info.get("operatingMargins"),
            "profit_margin": info.get("profitMargins"),
            "return_on_equity": info.get("returnOnEquity"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "free_cashflow": info.get("freeCashflow"),
            "beta": info.get("beta"),
            "dividend_yield": info.get("dividendYield"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_financial_metrics(%s) failed: %s", symbol, exc)
        return {"ticker": symbol.upper(), "error": str(exc)}
