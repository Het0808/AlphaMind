"""Financial Modeling Prep (FMP) provider — "stable" API.

Rich, normalized fundamentals + market data. Requires an API key (free tier).
Its annual income statement shares EDGAR's reporting period, so FMP acts as a
third corroborating source for revenue / net income / EPS cross-verification.
Gracefully unavailable when no key is configured.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from ..exceptions import (
    MissingCredentials,
    ProviderUnavailable,
    RateLimited,
    TickerNotFound,
)
from .base import FinancialProvider

logger = logging.getLogger(__name__)

_BASE = "https://financialmodelingprep.com/stable"


class FMPProvider(FinancialProvider):
    name = "fmp"

    def __init__(self, api_key: str = "", timeout: int = 20):
        self.api_key = api_key or ""
        self._timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key)

    def _get(self, endpoint: str, ticker: str, extra: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not self.api_key:
            raise MissingCredentials("FMP_API_KEY not set", provider=self.name)
        params = {"symbol": ticker, "apikey": self.api_key, **(extra or {})}
        try:
            resp = httpx.get(f"{_BASE}/{endpoint}", params=params, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(str(exc), provider=self.name) from exc

        if resp.status_code in (401, 403):
            raise MissingCredentials("FMP rejected the API key", provider=self.name)
        if resp.status_code == 402:
            # Free tier doesn't cover this symbol (e.g. NSE/.NS listings).
            raise ProviderUnavailable(f"{endpoint}: not covered by current FMP plan (HTTP 402)", provider=self.name)
        if resp.status_code == 429:
            raise RateLimited("FMP quota exceeded", provider=self.name)
        if resp.status_code >= 400:
            raise ProviderUnavailable(f"HTTP {resp.status_code}", provider=self.name)

        data = resp.json()
        if isinstance(data, dict) and data.get("Error Message"):
            raise ProviderUnavailable(data["Error Message"], provider=self.name)
        return data if isinstance(data, list) else [data]

    @staticmethod
    def _first(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        return rows[0] if rows else {}

    def get_overview(self, ticker: str) -> Dict[str, Any]:
        profile = self._first(self._get("profile", ticker))
        if not profile:
            raise TickerNotFound(ticker, provider=self.name)
        return {
            "name": profile.get("companyName"),
            "sector": profile.get("sector"),
            "industry": profile.get("industry"),
            "description": profile.get("description"),
            "exchange": profile.get("exchange") or profile.get("exchangeFullName"),
            "currency": profile.get("currency"),
            "country": profile.get("country"),
            "website": profile.get("website"),
            "employees": profile.get("fullTimeEmployees"),
        }

    def get_metrics(self, ticker: str) -> Dict[str, Any]:
        profile = self._first(self._get("profile", ticker))
        income = self._first(self._get("income-statement", ticker, {"period": "annual", "limit": 1}))
        cash = self._first(self._get("cash-flow-statement", ticker, {"period": "annual", "limit": 1}))
        ratios = self._first(self._get("ratios-ttm", ticker))
        key = self._first(self._get("key-metrics-ttm", ticker))

        if not any((profile, income, cash, ratios)):
            raise TickerNotFound(ticker, provider=self.name)

        year = income.get("fiscalYear")
        return {
            "price": profile.get("price"),
            "revenue": income.get("revenue"),
            "net_income": income.get("netIncome"),
            "eps": income.get("eps") or income.get("epsDiluted"),
            "market_cap": profile.get("marketCap"),
            "pe_ratio": ratios.get("priceToEarningsRatioTTM"),
            "ebitda": income.get("ebitda"),
            "operating_cash_flow": cash.get("operatingCashFlow"),
            "free_cash_flow": cash.get("freeCashFlow"),
            "enterprise_value": key.get("enterpriseValueTTM"),
            # Annual income statement → same reporting period as EDGAR (cross-verify).
            "fiscal_period": f"FY {year}" if year else "annual",
            "currency": income.get("reportedCurrency") or profile.get("currency"),
        }
