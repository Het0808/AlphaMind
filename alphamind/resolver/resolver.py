"""The resolver: company name / ticker → canonical ticker, with suggestions.

Resolution order:
  1. Exact alias / company-name / known-ticker hit (case-insensitive).
  2. Symbol pass-through — anything shaped like a US symbol (1-5 letters) or an
     Indian symbol (``*.NS`` / ``*.BO``) is accepted as a ticker.
  3. Otherwise → `TickerResolutionError` with fuzzy close-match suggestions.

Optionally enriches an unknown pass-through symbol's company name via the data
layer (yfinance), but never depends on it.
"""

from __future__ import annotations

import difflib
import logging
import re

from .aliases import ALIAS_NAMES, ALIAS_TO_TICKER, TICKER_TO_NAME, TICKER_TO_REGION
from .exceptions import TickerResolutionError
from .schemas import TickerResolution, TickerSuggestion

logger = logging.getLogger(__name__)

_US_SYMBOL = re.compile(r"^[A-Z]{1,5}$")
_INDIAN_SYMBOL = re.compile(r"^[A-Z0-9]{1,15}\.(NS|BO)$")


def _exchange_region(ticker: str) -> tuple[str, str]:
    if ticker.endswith(".NS"):
        return "NSE", "IN"
    if ticker.endswith(".BO"):
        return "BSE", "IN"
    return "US", TICKER_TO_REGION.get(ticker, "US")


def suggest_tickers(query: str, *, n: int = 5) -> list[TickerSuggestion]:
    """Return up to `n` close-match suggestions for an unresolved query."""
    names = difflib.get_close_matches(query.strip().lower(),
                                      [a for a in ALIAS_TO_TICKER], n=n, cutoff=0.6)
    seen, out = set(), []
    for key in names:
        ticker = ALIAS_TO_TICKER[key]
        if ticker in seen:
            continue
        seen.add(ticker)
        out.append(TickerSuggestion(company_name=TICKER_TO_NAME.get(ticker, ticker), ticker=ticker))
    return out[:n]


class TickerResolver:
    def resolve(self, query: str, *, enrich: bool = False) -> TickerResolution:
        if not query or not query.strip():
            raise TickerResolutionError(query or "", [])
        raw = query.strip()
        key = raw.lower()

        # 1. Exact alias / name / known ticker.
        if key in ALIAS_TO_TICKER:
            ticker = ALIAS_TO_TICKER[key]
            exchange, region = _exchange_region(ticker)
            return TickerResolution(
                query=raw, ticker=ticker, company_name=TICKER_TO_NAME[ticker],
                exchange=exchange, region=region, matched_by="alias",
            )

        # 2. Symbol pass-through (US or Indian).
        upper = raw.upper()
        if _US_SYMBOL.match(upper) or _INDIAN_SYMBOL.match(upper):
            name = TICKER_TO_NAME.get(upper) or (self._enrich_name(upper) if enrich else "") or upper
            exchange, region = _exchange_region(upper)
            return TickerResolution(
                query=raw, ticker=upper, company_name=name,
                exchange=exchange, region=region, matched_by="symbol",
            )

        # 3. Unresolved → suggestions.
        raise TickerResolutionError(raw, suggest_tickers(raw))

    @staticmethod
    def _enrich_name(ticker: str) -> str:
        try:
            from ..tools import get_company_overview

            ov = get_company_overview(ticker)
            return ov.get("name") or ""
        except Exception:  # noqa: BLE001 - enrichment is best-effort
            return ""


_default = TickerResolver()


def resolve_ticker(query: str, *, enrich: bool = False) -> TickerResolution:
    """Resolve a company name or symbol to a canonical ticker.

    Logs the input and the resolution so the pipeline is auditable.
    """
    resolution = _default.resolve(query, enrich=enrich)
    logger.info(
        "resolve: input=%r -> company=%r ticker=%r (%s, via %s)",
        query, resolution.company_name, resolution.ticker, resolution.region, resolution.matched_by,
    )
    return resolution
