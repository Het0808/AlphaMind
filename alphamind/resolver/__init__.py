"""Ticker Resolution Layer.

Turns free-form user input — a company name OR a ticker symbol, US or Indian —
into a validated, canonical ticker. Examples:

    Apple     -> AAPL
    Microsoft -> MSFT
    Tesla     -> TSLA
    NVIDIA    -> NVDA
    Reliance  -> RELIANCE.NS
    Infosys   -> INFY.NS
    TCS       -> TCS.NS

On failure it raises `TickerResolutionError` carrying close-match suggestions.
"""

from .exceptions import TickerResolutionError
from .resolver import TickerResolver, resolve_ticker, suggest_tickers
from .schemas import TickerResolution, TickerSuggestion

__all__ = [
    "TickerResolver",
    "resolve_ticker",
    "suggest_tickers",
    "TickerResolution",
    "TickerSuggestion",
    "TickerResolutionError",
]
