"""Download SEC filings from EDGAR.

Lists a company's recent 10-K/10-Q filings via the submissions API and fetches
the primary document. Reuses the shared ticker→CIK map cache key with the data
layer and honours SEC's User-Agent requirement and rate limits.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

import httpx

from ..config import get_settings
from ..data.cache import TTLCache
from ..data.exceptions import ProviderUnavailable, RateLimited, TickerNotFound
from .schemas import FilingRef

logger = logging.getLogger(__name__)

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_nodash}/{doc}"


class SECFilingsClient:
    def __init__(self, user_agent: Optional[str] = None, cache: Optional[TTLCache] = None, timeout: int = 30):
        self.user_agent = user_agent or get_settings().sec_user_agent
        self._cache = cache or TTLCache(ttl_seconds=86_400)
        self._timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}

    def _get(self, url: str, *, as_json: bool = True):
        try:
            resp = httpx.get(url, headers=self._headers(), timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(str(exc), provider="sec_edgar") from exc
        if resp.status_code == 404:
            raise TickerNotFound(url, provider="sec_edgar")
        if resp.status_code == 429:
            raise RateLimited("SEC rate limit hit", provider="sec_edgar")
        if resp.status_code >= 400:
            raise ProviderUnavailable(f"HTTP {resp.status_code}", provider="sec_edgar")
        return resp.json() if as_json else resp.text

    def cik(self, ticker: str) -> int:
        cached = self._cache.get("edgar:cikmap")
        if cached is None:
            cached = {
                row["ticker"].upper(): int(row["cik_str"])
                for row in self._get(_TICKERS_URL).values()
            }
            self._cache.set("edgar:cikmap", cached)
        cik = cached.get(ticker.upper())
        if cik is None:
            raise TickerNotFound(ticker, provider="sec_edgar")
        return cik

    def list_filings(
        self,
        ticker: str,
        forms: Sequence[str] = ("10-K", "10-Q"),
        limit: int = 4,
    ) -> List[FilingRef]:
        """Return the most recent filings of the given form types."""
        ticker = ticker.upper()
        cik = self.cik(ticker)
        data = self._get(_SUBMISSIONS_URL.format(cik=cik))
        recent = data.get("filings", {}).get("recent", {})

        accession = recent.get("accessionNumber", [])
        form = recent.get("form", [])
        filing_date = recent.get("filingDate", [])
        report_date = recent.get("reportDate", [])
        primary_doc = recent.get("primaryDocument", [])

        wanted = {f.upper() for f in forms}
        out: List[FilingRef] = []
        for i in range(len(accession)):
            if form[i].upper() not in wanted:
                continue
            acc = accession[i]
            doc = primary_doc[i]
            out.append(
                FilingRef(
                    ticker=ticker,
                    cik=cik,
                    form=form[i],
                    accession=acc,
                    filing_date=filing_date[i],
                    period_of_report=report_date[i] if i < len(report_date) else None,
                    primary_document=doc,
                    url=_ARCHIVE_URL.format(cik=cik, acc_nodash=acc.replace("-", ""), doc=doc),
                )
            )
            if len(out) >= limit:
                break
        return out

    def fetch_document(self, ref: FilingRef) -> str:
        """Fetch the raw HTML of a filing's primary document."""
        return self._get(ref.url, as_json=False)
