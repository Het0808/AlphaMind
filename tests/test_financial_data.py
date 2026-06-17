"""Offline tests for the financial data layer — no network or API keys needed.

Fake providers exercise merging, provenance, validation/sanitization, caching and
ticker validation deterministically.
"""

import pytest

from alphamind.data import FinancialDataService
from alphamind.data.cache import TTLCache
from alphamind.data.exceptions import InvalidTicker, TickerNotFound
from alphamind.data.providers.base import FinancialProvider
from alphamind.data.schemas import is_valid_ticker


class FakeFMP(FinancialProvider):
    """Has market data but a NaN revenue (should be sanitized to None)."""

    name = "fake_fmp"

    def get_overview(self, ticker):
        return {"name": "Acme Corp", "sector": "Tech", "industry": None}

    def get_metrics(self, ticker):
        return {"market_cap": 1_000.0, "pe_ratio": 25.0, "revenue": float("nan")}


class FakeEdgar(FinancialProvider):
    """Authoritative fundamentals; backfills fields FMP lacked."""

    name = "fake_edgar"

    def get_overview(self, ticker):
        return {"industry": "Software", "country": "United States"}

    def get_metrics(self, ticker):
        return {"revenue": 500.0, "net_income": 90.0, "eps": 4.2}


class Flaky(FinancialProvider):
    name = "flaky"

    def get_overview(self, ticker):
        raise RuntimeError("boom")

    def get_metrics(self, ticker):
        raise RuntimeError("boom")


def make_service(providers):
    return FinancialDataService(providers=providers, cache=TTLCache(ttl_seconds=60))


def test_merge_and_provenance():
    svc = make_service([FakeFMP(), FakeEdgar()])
    snap = svc.get_snapshot("AAPL")

    # FMP wins where present; EDGAR backfills the gaps.
    assert snap.overview.name == "Acme Corp"
    assert snap.overview.industry == "Software"        # backfilled by EDGAR
    assert snap.metrics.market_cap == 1_000.0          # from FMP
    assert snap.metrics.revenue == 500.0               # FMP's NaN dropped -> EDGAR used
    assert snap.field_sources["revenue"] == "fake_edgar"
    assert snap.field_sources["market_cap"] == "fake_fmp"
    assert set(snap.providers_used) == {"fake_fmp", "fake_edgar"}


def test_nan_is_sanitized():
    svc = make_service([FakeFMP()])
    snap = svc.get_snapshot("AAPL")
    assert snap.metrics.revenue is None  # NaN never leaks into the model


def test_flaky_provider_is_isolated():
    svc = make_service([Flaky(), FakeEdgar()])
    snap = svc.get_snapshot("AAPL")
    assert snap.metrics.revenue == 500.0
    assert any("flaky" in w for w in snap.warnings)


def test_unknown_ticker_raises():
    svc = make_service([Flaky()])
    with pytest.raises(TickerNotFound):
        svc.get_snapshot("AAPL")


def test_invalid_ticker_rejected_before_network():
    svc = make_service([FakeEdgar()])
    with pytest.raises(InvalidTicker):
        svc.get_snapshot("not a ticker!!")


def test_caching_avoids_second_call():
    provider = FakeEdgar()
    calls = {"n": 0}
    original = provider.get_metrics

    def counting(ticker):
        calls["n"] += 1
        return original(ticker)

    provider.get_metrics = counting
    svc = make_service([provider])

    svc.get_snapshot("AAPL")
    svc.get_snapshot("AAPL")  # served from cache
    assert calls["n"] == 1

    svc.get_snapshot("AAPL", force_refresh=True)
    assert calls["n"] == 2


@pytest.mark.parametrize("ticker,valid", [("AAPL", True), ("BRK.B", True), ("", False), ("toolongticker", False)])
def test_ticker_validation(ticker, valid):
    assert is_valid_ticker(ticker) is valid
