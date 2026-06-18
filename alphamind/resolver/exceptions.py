"""Resolution errors with actionable suggestions."""

from __future__ import annotations

from typing import List

from .schemas import TickerSuggestion


class TickerResolutionError(ValueError):
    """Raised when a query can't be resolved to a ticker.

    Carries `suggestions` (close matches) so callers can return a helpful message.
    """

    def __init__(self, query: str, suggestions: List[TickerSuggestion] | None = None):
        self.query = query
        self.suggestions = suggestions or []
        hint = ""
        if self.suggestions:
            hint = " Did you mean: " + ", ".join(f"{s.company_name} ({s.ticker})" for s in self.suggestions) + "?"
        super().__init__(f"Could not resolve '{query}' to a ticker.{hint}")
