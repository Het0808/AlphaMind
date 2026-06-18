"""Yahoo Finance provider (via yfinance).

Strong for live market data (market cap, trailing PE, EPS) and a decent company
profile. No credentials required. Used as the default backbone provider.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ..exceptions import ProviderUnavailable, TickerNotFound
from .base import FinancialProvider

logger = logging.getLogger(__name__)


class YahooProvider(FinancialProvider):
    name = "yahoo"

    def _info(self, ticker: str) -> Dict[str, Any]:
        try:
            import yfinance as yf

            info = yf.Ticker(ticker).info or {}
        except ImportError as exc:  # pragma: no cover - dependency missing
            raise ProviderUnavailable("yfinance not installed", provider=self.name) from exc
        except Exception as exc:  # noqa: BLE001 - network/parse errors
            raise ProviderUnavailable(str(exc), provider=self.name) from exc

        # yfinance returns a near-empty dict for unknown symbols.
        if not info.get("longName") and not info.get("shortName") and not info.get("quoteType"):
            raise TickerNotFound(ticker, provider=self.name)
        return info

    def get_overview(self, ticker: str) -> Dict[str, Any]:
        info = self._info(ticker)
        return {
            "name": info.get("longName") or info.get("shortName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "description": info.get("longBusinessSummary"),
            "exchange": info.get("exchange") or info.get("fullExchangeName"),
            "currency": info.get("financialCurrency") or info.get("currency"),
            "country": info.get("country"),
            "website": info.get("website"),
            "employees": info.get("fullTimeEmployees"),
        }

    def get_metrics(self, ticker: str) -> Dict[str, Any]:
        info = self._info(ticker)
        return {
            "price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "revenue": info.get("totalRevenue"),
            "net_income": info.get("netIncomeToCommon"),
            "eps": info.get("trailingEps"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "ebitda": info.get("ebitda"),
            "operating_cash_flow": info.get("operatingCashflow"),
            "free_cash_flow": info.get("freeCashflow"),
            "enterprise_value": info.get("enterpriseValue"),
            "roe": info.get("returnOnEquity"),
            "fiscal_period": "TTM",
            "currency": info.get("financialCurrency") or info.get("currency"),
        }
