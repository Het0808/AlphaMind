"""Data-access tools used by the specialist agents."""

from .financials import (
    get_company_overview,
    get_financial_snapshot,
    get_key_financials,
)
from .market_data import get_company_profile, get_financial_metrics
from .news_feed import get_recent_news
from .research_rag import search_filings

__all__ = [
    # Multi-source financial data (Yahoo + SEC EDGAR + FMP)
    "get_financial_snapshot",
    "get_company_overview",
    "get_key_financials",
    # RAG over SEC filings (returns exact citations)
    "search_filings",
    # Legacy single-source helpers
    "get_company_profile",
    "get_financial_metrics",
    "get_recent_news",
]
