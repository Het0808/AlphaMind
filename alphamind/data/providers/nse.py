"""NSE (National Stock Exchange of India) provider — second source for Indian stocks.

Adds price, P/E and a derived market cap for `.NS` listings so Indian stocks can be
cross-verified against Yahoo (NSE doesn't expose revenue/net-income, so those stay
single-source). Fundamentals fields are intentionally absent.

NSE's public API sits behind Akamai bot protection and frequently returns 403 to
datacenter/non-browser clients. This provider primes a browser-like session and
**degrades gracefully** (raises ProviderUnavailable → recorded as a warning) when
blocked, exactly like every other provider. It only touches the network for Indian
tickers, so US requests pay nothing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from ..cache import TTLCache
from ..exceptions import ProviderUnavailable, TickerNotFound
from .base import FinancialProvider

logger = logging.getLogger(__name__)

_BASE = "https://www.nseindia.com"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": f"{_BASE}/get-quotes/equity",
}


def parse_quote(d: Dict[str, Any]) -> Dict[str, Any]:
    """Map an NSE quote-equity payload to our metric fields (pure / testable)."""
    pi = d.get("priceInfo") or {}
    md = d.get("metadata") or {}
    si = d.get("securityInfo") or {}
    last = pi.get("lastPrice")
    issued = si.get("issuedSize")
    market_cap = last * issued if isinstance(last, (int, float)) and isinstance(issued, (int, float)) else None
    return {
        "price": last,
        "pe_ratio": md.get("pdSymbolPe"),
        "market_cap": market_cap,
        "currency": "INR",
        "fiscal_period": "spot",
    }


class NSEProvider(FinancialProvider):
    name = "nse"

    def __init__(self, cache: Optional[TTLCache] = None, timeout: int = 8):
        self._cache = cache or TTLCache(ttl_seconds=600)
        self._timeout = timeout
        self._client: Optional[httpx.Client] = None

    @staticmethod
    def _nse_symbol(ticker: str) -> Optional[str]:
        t = ticker.upper()
        return t.split(".")[0] if t.endswith((".NS", ".BO")) else None

    def _session(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(headers=_HEADERS, timeout=self._timeout, follow_redirects=True)
            try:
                self._client.get(_BASE)  # prime cookies
            except httpx.HTTPError:
                pass
        return self._client

    def _quote(self, symbol: str) -> Dict[str, Any]:
        cache_key = f"nse:quote:{symbol}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            resp = self._session().get(f"{_BASE}/api/quote-equity", params={"symbol": symbol})
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(str(exc), provider=self.name) from exc
        if resp.status_code in (401, 403):
            raise ProviderUnavailable("NSE blocked the request (bot protection)", provider=self.name)
        if resp.status_code == 404:
            raise TickerNotFound(symbol, provider=self.name)
        if resp.status_code >= 400:
            raise ProviderUnavailable(f"HTTP {resp.status_code}", provider=self.name)
        try:
            data = resp.json()
        except ValueError as exc:
            raise ProviderUnavailable("NSE returned non-JSON", provider=self.name) from exc
        self._cache.set(cache_key, data)
        return data

    def get_overview(self, ticker: str) -> Dict[str, Any]:
        symbol = self._nse_symbol(ticker)
        if symbol is None:
            return {}  # not an Indian listing — no NSE data
        info = (self._quote(symbol).get("info") or {})
        return {"name": info.get("companyName"), "currency": "INR", "exchange": "NSE"}

    def get_metrics(self, ticker: str) -> Dict[str, Any]:
        symbol = self._nse_symbol(ticker)
        if symbol is None:
            return {}
        return parse_quote(self._quote(symbol))
