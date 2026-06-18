"""Provider interface.

A provider returns *partial* normalized dicts keyed by the canonical field names
in `schemas.OVERVIEW_FIELDS` / `schemas.METRIC_FIELDS`. Missing data is simply
absent or `None`; providers must never invent values. Failures are raised as
`DataProviderError` subclasses so the service can handle them per-provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class FinancialProvider(ABC):
    #: Stable identifier used in provenance / logs.
    name: str = "base"

    def available(self) -> bool:
        """Whether this provider is usable (e.g. has required credentials)."""
        return True

    @abstractmethod
    def get_overview(self, ticker: str) -> Dict[str, Any]:
        """Return a partial company-overview dict (may be empty)."""

    @abstractmethod
    def get_metrics(self, ticker: str) -> Dict[str, Any]:
        """Return a partial financial-metrics dict (may be empty)."""
