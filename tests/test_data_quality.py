"""Tests for the financial data-quality system.

Covers the required tickers — TCS.NS, INFY.NS, RELIANCE.NS (INR) and AAPL, MSFT,
NVDA (USD) — using deterministic fake providers so cross-source verification,
validation, confidence and the fail-safe are reproducible without network/keys.
"""

import pytest

from alphamind.data.providers.base import FinancialProvider
from alphamind.data.service import FinancialDataService
from alphamind.data.validation import validate_metrics
from alphamind.data.schemas import FinancialMetrics


# ── Fixture data: realistic-ish values per ticker (USD for US, INR for Indian) ──
US = {
    "AAPL": dict(price=232.0, revenue=4.16e11, net_income=1.12e11, eps=7.46, market_cap=3.5e12, pe_ratio=31.0, currency="USD"),
    "MSFT": dict(price=512.0, revenue=2.81e11, net_income=1.01e11, eps=13.64, market_cap=3.3e12, pe_ratio=37.0, currency="USD"),
    "NVDA": dict(price=182.0, revenue=1.30e11, net_income=7.3e10, eps=2.94, market_cap=3.1e12, pe_ratio=48.0, currency="USD"),
}
IN = {
    "TCS.NS": dict(revenue=2.4e12, net_income=4.6e11, eps=126.0, market_cap=1.4e13, pe_ratio=29.0, currency="INR"),
    "INFY.NS": dict(revenue=1.5e12, net_income=2.6e11, eps=63.0, market_cap=6.6e12, pe_ratio=25.0, currency="INR"),
    "RELIANCE.NS": dict(revenue=9.0e12, net_income=7.0e11, eps=100.0, market_cap=1.9e13, pe_ratio=27.0, currency="INR"),
}


class FakeProvider(FinancialProvider):
    def __init__(self, name, table, jitter=0.0):
        self.name = name
        self._table = table
        self._jitter = jitter  # relative perturbation to simulate source disagreement

    def get_overview(self, ticker):
        return {"name": ticker.split(".")[0], "currency": self._table.get(ticker, {}).get("currency")}

    def get_metrics(self, ticker):
        row = self._table.get(ticker)
        if not row:
            return {}
        out = {}
        for k, v in row.items():
            out[k] = v * (1 + self._jitter) if isinstance(v, (int, float)) and self._jitter else v
        return out


def make_service(providers):
    return FinancialDataService(providers=providers)


@pytest.mark.parametrize("ticker", list(US) + list(IN))
def test_snapshot_currency_and_availability(ticker):
    table = {**US, **IN}
    # Two corroborating sources (edgar + a close second) → high confidence.
    svc = make_service([
        FakeProvider("sec_edgar", table),
        FakeProvider("yahoo", table, jitter=0.005),  # within 2% tolerance
    ])
    snap = svc.get_snapshot(ticker)

    expected_cur = "INR" if ticker.endswith(".NS") else "USD"
    assert snap.metrics.currency == expected_cur
    assert snap.metrics.market_cap is not None       # available, not failed-safe
    q = snap.quality.field_quality["market_cap"]
    assert q.status == "ok" and q.confidence >= 0.8   # corroborated
    assert q.agreement is not None and q.agreement >= 0.8


def test_cross_source_disagreement_lowers_confidence():
    table = {"AAPL": US["AAPL"]}
    svc = make_service([
        FakeProvider("sec_edgar", table),
        FakeProvider("yahoo", table, jitter=0.5),  # 50% off → disagreement
    ])
    snap = svc.get_snapshot("AAPL")
    q = snap.quality.field_quality["market_cap"]
    assert q.status == "disagreement"
    assert q.confidence < 0.6
    assert len(q.sources) == 2


def test_fail_safe_hides_out_of_range_value():
    bad = {"AAPL": {**US["AAPL"], "pe_ratio": 99999.0}}  # impossible P/E
    svc = make_service([FakeProvider("sec_edgar", bad)])
    snap = svc.get_snapshot("AAPL")
    # Out-of-range → validation error → confidence crushed → hidden.
    assert snap.metrics.pe_ratio is None
    assert snap.quality.field_quality["pe_ratio"].status == "unavailable"
    assert any("pe_ratio" in w for w in snap.warnings)


def test_validation_layers_flag_issues():
    # Indian ticker reporting USD → currency error; FCF > OCF → cross-field warning.
    m = FinancialMetrics(ticker="TCS.NS", currency="USD",
                         operating_cash_flow=100, free_cash_flow=200, roe=15)
    issues = {(i.field, i.severity) for i in validate_metrics(m, "TCS.NS")}
    assert ("currency", "error") in issues
    assert ("free_cash_flow", "warning") in issues
    assert ("roe", "warning") in issues  # 15 looks like percent not fraction


def test_single_source_is_lower_confidence_than_corroborated():
    table = {"NVDA": US["NVDA"]}
    one = make_service([FakeProvider("yahoo", table)]).get_snapshot("NVDA")
    two = make_service([
        FakeProvider("sec_edgar", table), FakeProvider("yahoo", table, jitter=0.003),
    ]).get_snapshot("NVDA")
    assert one.quality.field_quality["revenue"].status == "single_source"
    assert two.quality.field_quality["revenue"].confidence > one.quality.field_quality["revenue"].confidence


def test_overall_confidence_and_provenance():
    table = {"INFY.NS": IN["INFY.NS"]}
    snap = make_service([FakeProvider("sec_edgar", table)]).get_snapshot("INFY.NS")
    assert 0.0 < snap.quality.overall_confidence <= 1.0
    assert "sec_edgar" in snap.quality.providers
    assert snap.quality.field_quality["revenue"].chosen_source == "sec_edgar"
