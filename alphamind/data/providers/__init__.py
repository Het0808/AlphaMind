"""Concrete financial-data providers.

Each provider implements the `FinancialProvider` interface and returns *partial*
normalized dicts. The service merges them, so any single provider being down only
degrades coverage rather than failing the request.
"""

from .base import FinancialProvider
from .edgar import EdgarProvider
from .fmp import FMPProvider
from .yahoo import YahooProvider

__all__ = ["FinancialProvider", "YahooProvider", "EdgarProvider", "FMPProvider"]
