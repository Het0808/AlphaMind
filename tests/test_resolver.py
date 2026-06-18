"""Unit tests for the Ticker Resolution Layer.

Covers the required companies (Apple, Microsoft, Tesla, NVIDIA, Reliance,
Infosys), TCS, symbol pass-through, case-insensitivity, Indian symbols, and the
unresolved-with-suggestions path.
"""

import pytest

from alphamind.resolver import TickerResolutionError, resolve_ticker, suggest_tickers


@pytest.mark.parametrize(
    "query,expected_ticker,region",
    [
        ("Apple", "AAPL", "US"),
        ("apple", "AAPL", "US"),          # case-insensitive
        ("Microsoft", "MSFT", "US"),
        ("Tesla", "TSLA", "US"),
        ("NVIDIA", "NVDA", "US"),
        ("nvidia", "NVDA", "US"),
        ("Reliance", "RELIANCE.NS", "IN"),
        ("Infosys", "INFY.NS", "IN"),
        ("TCS", "TCS.NS", "IN"),
        ("Tata Consultancy Services", "TCS.NS", "IN"),
    ],
)
def test_resolves_required_companies(query, expected_ticker, region):
    res = resolve_ticker(query)
    assert res.ticker == expected_ticker
    assert res.region == region
    assert res.company_name  # non-empty


def test_symbol_passthrough_known_and_unknown():
    known = resolve_ticker("AAPL")
    assert known.ticker == "AAPL" and known.company_name == "Apple Inc." and known.matched_by in {"alias", "symbol"}

    unknown = resolve_ticker("ZZZZ")   # valid US-shaped symbol, not in registry
    assert unknown.ticker == "ZZZZ" and unknown.matched_by == "symbol"


def test_indian_symbol_passthrough():
    res = resolve_ticker("RELIANCE.NS")
    assert res.ticker == "RELIANCE.NS" and res.region == "IN" and res.exchange == "NSE"
    bse = resolve_ticker("500325.BO")
    assert bse.exchange == "BSE" and bse.region == "IN"


def test_unresolved_raises_with_suggestions():
    with pytest.raises(TickerResolutionError) as ei:
        resolve_ticker("Appl Inc")   # typo → should suggest Apple
    assert ei.value.suggestions
    assert any(s.ticker == "AAPL" for s in ei.value.suggestions)


def test_empty_query_raises():
    with pytest.raises(TickerResolutionError):
        resolve_ticker("   ")


def test_suggest_helper():
    sugg = suggest_tickers("microsft")   # typo
    assert any(s.ticker == "MSFT" for s in sugg)
