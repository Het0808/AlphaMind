"""SEC EDGAR provider (official data.sec.gov XBRL API).

Authoritative, free, audited fundamentals straight from 10-K/10-Q filings:
revenue, net income, EPS and operating cash flow (free cash flow derived as
operating cash flow minus capex). No market data (price/PE/market cap).

SEC requires a descriptive `User-Agent` with contact info and rate-limits to
~10 req/s; we cache the ticker→CIK map and per-company facts to stay well under.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..cache import TTLCache
from ..exceptions import ProviderUnavailable, RateLimited, TickerNotFound
from .base import FinancialProvider

logger = logging.getLogger(__name__)

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# Candidate us-gaap tags, in preference order, for each metric.
_REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
]
_NET_INCOME_TAGS = ["NetIncomeLoss"]
_EPS_TAGS = ["EarningsPerShareDiluted", "EarningsPerShareBasic"]
_OCF_TAGS = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
]
_CAPEX_TAGS = ["PaymentsToAcquirePropertyPlantAndEquipment"]


class EdgarProvider(FinancialProvider):
    name = "sec_edgar"

    def __init__(self, user_agent: str, cache: Optional[TTLCache] = None, timeout: int = 30):
        self.user_agent = user_agent
        self._cache = cache or TTLCache(ttl_seconds=86_400)
        self._timeout = timeout

    # ── HTTP helpers ───────────────────────────────────────────────────
    def _headers(self) -> Dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}

    def _get_json(self, url: str) -> Any:
        try:
            resp = httpx.get(url, headers=self._headers(), timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(str(exc), provider=self.name) from exc
        if resp.status_code == 404:
            raise TickerNotFound(url, provider=self.name)
        if resp.status_code == 429:
            raise RateLimited("SEC rate limit hit", provider=self.name)
        if resp.status_code >= 400:
            raise ProviderUnavailable(f"HTTP {resp.status_code}", provider=self.name)
        return resp.json()

    def _cik(self, ticker: str) -> int:
        cached = self._cache.get("edgar:cikmap")
        if cached is None:
            cached = {
                row["ticker"].upper(): int(row["cik_str"])
                for row in self._get_json(_TICKERS_URL).values()
            }
            self._cache.set("edgar:cikmap", cached)
        cik = cached.get(ticker.upper())
        if cik is None:
            raise TickerNotFound(ticker, provider=self.name)
        return cik

    def _facts(self, ticker: str) -> Dict[str, Any]:
        key = f"edgar:facts:{ticker.upper()}"
        cached = self._cache.get(key)
        if cached is None:
            cached = self._get_json(_FACTS_URL.format(cik=self._cik(ticker)))
            self._cache.set(key, cached)
        return cached

    # ── Extraction ─────────────────────────────────────────────────────
    @staticmethod
    def _latest_annual(facts: Dict[str, Any], tags: List[str], unit: str) -> Tuple[Optional[float], Optional[str]]:
        """Most recent full-year (10-K / fp=FY) value across candidate tags."""
        gaap = facts.get("facts", {}).get("us-gaap", {})
        for tag in tags:
            units = gaap.get(tag, {}).get("units", {}).get(unit, [])
            annual = [u for u in units if u.get("form") == "10-K" and u.get("fp") == "FY"]
            pool = annual or units
            if not pool:
                continue
            best = max(pool, key=lambda u: u.get("end", ""))
            return best.get("val"), best.get("end")
        return None, None

    def get_overview(self, ticker: str) -> Dict[str, Any]:
        data = self._get_json(_SUBMISSIONS_URL.format(cik=self._cik(ticker)))
        exchanges = data.get("exchanges") or []
        addr = (data.get("addresses") or {}).get("business") or {}
        return {
            "name": data.get("name"),
            "industry": data.get("sicDescription"),
            "exchange": exchanges[0] if exchanges else None,
            "country": addr.get("stateOrCountryDescription") or addr.get("stateOrCountry"),
            "currency": "USD",
        }

    def get_metrics(self, ticker: str) -> Dict[str, Any]:
        facts = self._facts(ticker)
        revenue, period = self._latest_annual(facts, _REVENUE_TAGS, "USD")
        net_income, _ = self._latest_annual(facts, _NET_INCOME_TAGS, "USD")
        eps, _ = self._latest_annual(facts, _EPS_TAGS, "USD/shares")
        ocf, _ = self._latest_annual(facts, _OCF_TAGS, "USD")
        capex, _ = self._latest_annual(facts, _CAPEX_TAGS, "USD")

        free_cash_flow = None
        if ocf is not None and capex is not None:
            free_cash_flow = ocf - capex  # capex is reported as a positive outflow

        return {
            "revenue": revenue,
            "net_income": net_income,
            "eps": eps,
            "operating_cash_flow": ocf,
            "free_cash_flow": free_cash_flow,
            "fiscal_period": f"FY ending {period}" if period else "FY",
            "currency": "USD",
        }
