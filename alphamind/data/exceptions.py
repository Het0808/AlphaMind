"""Typed exceptions for the financial data layer.

Providers raise these so the service can react precisely: skip an unavailable
provider, surface a not-found ticker, back off on rate limits, etc. — instead of
catching bare `Exception` everywhere.
"""

from __future__ import annotations


class DataProviderError(Exception):
    """Base class for all data-layer failures."""

    def __init__(self, message: str, *, provider: str | None = None):
        self.provider = provider
        super().__init__(f"[{provider or 'data'}] {message}")


class ProviderUnavailable(DataProviderError):
    """Network error, timeout, or 5xx from an upstream provider."""


class TickerNotFound(DataProviderError):
    """The provider has no record for the requested ticker."""


class RateLimited(DataProviderError):
    """The provider returned 429 / quota exceeded."""


class MissingCredentials(DataProviderError):
    """A required API key / credential is not configured."""


class InvalidTicker(DataProviderError):
    """The ticker failed format validation before any request was made."""
