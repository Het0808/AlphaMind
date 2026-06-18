"""AlphaMind financial data layer.

A provider-agnostic service that fetches, validates, merges and caches real
financial data from Yahoo Finance, SEC EDGAR and Financial Modeling Prep.
"""

from .exceptions import (
    DataProviderError,
    MissingCredentials,
    ProviderUnavailable,
    RateLimited,
    TickerNotFound,
)
from .schemas import CompanyOverview, FinancialMetrics, FinancialSnapshot
from .service import FinancialDataService, get_financial_service

__all__ = [
    "FinancialDataService",
    "get_financial_service",
    "FinancialSnapshot",
    "CompanyOverview",
    "FinancialMetrics",
    "DataProviderError",
    "ProviderUnavailable",
    "TickerNotFound",
    "RateLimited",
    "MissingCredentials",
]
