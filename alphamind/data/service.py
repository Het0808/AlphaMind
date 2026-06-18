"""FinancialDataService — the single entry point for real financial data.

Responsibilities:
  • Validate the ticker before any network call.
  • Query every available provider, tolerating per-provider failures.
  • Merge partial results field-by-field (first non-None wins, by priority) and
    record which provider supplied each field (provenance).
  • Validate/sanitize the merged result into typed Pydantic models.
  • Cache the finished snapshot per ticker for `cache_ttl` seconds.

Provider priority (configurable): FMP → Yahoo → SEC EDGAR. FMP and Yahoo lead for
market data; EDGAR backfills authoritative fundamentals when the others lack them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict, List, Optional

from ..config import get_settings
from .cache import TTLCache
from .exceptions import DataProviderError, InvalidTicker, TickerNotFound
from .providers import EdgarProvider, FinancialProvider, FMPProvider, YahooProvider
from .quality import apply_fail_safe, build_quality
from .schemas import (
    METRIC_FIELDS,
    OVERVIEW_FIELDS,
    CompanyOverview,
    FinancialMetrics,
    FinancialSnapshot,
    clean_field,
    is_valid_ticker,
    normalize_ticker,
)
from .validation import validate_metrics

logger = logging.getLogger(__name__)


def build_default_providers(settings=None, shared_cache: Optional[TTLCache] = None) -> List[FinancialProvider]:
    """Construct the default provider chain from settings (priority order)."""
    settings = settings or get_settings()
    providers: List[FinancialProvider] = []
    if getattr(settings, "enable_fmp", True):
        providers.append(FMPProvider(api_key=settings.fmp_api_key))
    if getattr(settings, "enable_yahoo", True):
        providers.append(YahooProvider())
    if getattr(settings, "enable_edgar", True):
        providers.append(EdgarProvider(user_agent=settings.sec_user_agent, cache=shared_cache))
    return providers


class FinancialDataService:
    def __init__(
        self,
        providers: Optional[List[FinancialProvider]] = None,
        *,
        cache: Optional[TTLCache] = None,
        cache_ttl: Optional[int] = None,
        settings=None,
    ):
        settings = settings or get_settings()
        self._cache = cache or TTLCache(ttl_seconds=cache_ttl or settings.data_cache_ttl)
        self._providers = providers if providers is not None else build_default_providers(settings, self._cache)
        # Only keep providers that are actually usable right now.
        self._active = [p for p in self._providers if p.available()]

    @property
    def active_providers(self) -> List[str]:
        return [p.name for p in self._active]

    # ── Public API ─────────────────────────────────────────────────────
    def get_snapshot(self, ticker: str, *, force_refresh: bool = False) -> FinancialSnapshot:
        """Return a validated, merged FinancialSnapshot for any public ticker."""
        ticker = normalize_ticker(ticker)
        if not is_valid_ticker(ticker):
            raise InvalidTicker(f"'{ticker}' is not a valid ticker symbol")

        cache_key = f"snapshot:{ticker}"
        if not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        settings = get_settings()
        overview_raw: Dict[str, Any] = {}
        metrics_raw: Dict[str, Any] = {}
        # candidates[field][provider] = value — powers cross-source verification.
        candidates: Dict[str, Dict[str, float]] = {}
        field_sources: Dict[str, str] = {}
        warnings: List[str] = []

        for provider in self._active:
            self._collect(provider, "overview", ticker, OVERVIEW_FIELDS, overview_raw, candidates, field_sources, warnings)
            self._collect(provider, "metrics", ticker, METRIC_FIELDS, metrics_raw, candidates, field_sources, warnings)

        if not overview_raw.get("name") and not any(metrics_raw.get(f) is not None for f in METRIC_FIELDS):
            raise TickerNotFound(f"No data found for '{ticker}' across {self.active_providers}")

        metrics = FinancialMetrics(ticker=ticker, **{k: metrics_raw.get(k) for k in METRIC_FIELDS})

        # Indian listings (.NS/.BO) are priced in INR — normalize any provider
        # that mislabels the currency (e.g. Yahoo returns USD for some .NS tickers).
        if ticker.endswith((".NS", ".BO")) and (metrics.currency or "").upper() != "INR":
            if metrics.currency:
                warnings.append(f"provider reported {metrics.currency} for Indian listing {ticker}; normalized to INR")
            metrics.currency = "INR"

        # ── Validate → score confidence → fail-safe ──
        issues = validate_metrics(metrics, ticker)
        providers_used = sorted(set(field_sources.values()))
        now = datetime.now(timezone.utc).isoformat()
        quality = build_quality(
            ticker=ticker,
            chosen={k: metrics_raw.get(k) for k in METRIC_FIELDS},
            candidates=candidates,
            field_sources=field_sources,
            currency=metrics.currency,
            issues=issues,
            providers=providers_used,
            tolerance=settings.cross_source_tolerance,
            threshold=settings.data_confidence_threshold,
            last_updated=now,
        )
        dropped = apply_fail_safe(metrics, quality, settings.data_confidence_threshold)
        if dropped:
            warnings.append(f"low-confidence fields hidden: {', '.join(dropped)}")

        snapshot = FinancialSnapshot(
            ticker=ticker,
            overview=CompanyOverview(ticker=ticker, name=overview_raw.get("name") or ticker, **{
                k: overview_raw.get(k) for k in OVERVIEW_FIELDS if k != "name"
            }),
            metrics=metrics,
            providers_used=providers_used,
            field_sources=field_sources,
            warnings=warnings,
            quality=quality,
            retrieved_at=now,
        )
        self._cache.set(cache_key, snapshot)
        return snapshot

    def get_overview(self, ticker: str, *, force_refresh: bool = False) -> CompanyOverview:
        return self.get_snapshot(ticker, force_refresh=force_refresh).overview

    def get_metrics(self, ticker: str, *, force_refresh: bool = False) -> FinancialMetrics:
        return self.get_snapshot(ticker, force_refresh=force_refresh).metrics

    # ── Internals ──────────────────────────────────────────────────────
    def _collect(
        self,
        provider: FinancialProvider,
        kind: str,
        ticker: str,
        fields: List[str],
        merged: Dict[str, Any],
        candidates: Dict[str, Dict[str, float]],
        field_sources: Dict[str, str],
        warnings: List[str],
    ) -> None:
        """Query one provider; fill missing fields AND record every candidate value."""
        fetch = provider.get_overview if kind == "overview" else provider.get_metrics
        try:
            data = fetch(ticker) or {}
        except DataProviderError as exc:
            warnings.append(str(exc))
            return
        except Exception as exc:  # noqa: BLE001 - never let one provider break the run
            logger.exception("Unexpected error from %s.%s", provider.name, kind)
            warnings.append(f"[{provider.name}] unexpected error: {exc}")
            return

        for field in fields:
            # Non-finite numbers (NaN/inf) are treated as absent so they don't
            # block a valid backfill from a lower-priority provider.
            value = clean_field(field, data.get(field))
            if value is None:
                continue
            # Record this provider's value for cross-source verification (numbers only).
            if isinstance(value, (int, float)):
                candidates.setdefault(field, {})[provider.name] = value
            # First provider (by priority) wins the "chosen" value.
            if merged.get(field) is None:
                merged[field] = value
                field_sources[field] = provider.name


@lru_cache
def get_financial_service() -> FinancialDataService:
    """Process-wide singleton so the cache and provider clients are reused."""
    return FinancialDataService()
