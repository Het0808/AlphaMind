"""Agent-facing tool wrappers over the FinancialDataService.

Agents (and LangGraph nodes) call these thin functions, which return plain,
JSON-serializable dicts ready to drop into an LLM prompt. All errors are caught
here and surfaced as an `error` field so a single data hiccup never crashes a run.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ..data import DataProviderError, get_financial_service

logger = logging.getLogger(__name__)


def get_financial_snapshot(ticker: str, *, force_refresh: bool = False) -> Dict[str, Any]:
    """Full overview + metrics + provenance for a ticker (dict form)."""
    try:
        snapshot = get_financial_service().get_snapshot(ticker, force_refresh=force_refresh)
        return snapshot.model_dump()
    except DataProviderError as exc:
        logger.warning("get_financial_snapshot(%s) failed: %s", ticker, exc)
        return {"ticker": ticker.upper(), "error": str(exc)}


def get_company_overview(ticker: str) -> Dict[str, Any]:
    """Company overview only (name, sector, industry, description, …)."""
    try:
        return get_financial_service().get_overview(ticker).model_dump()
    except DataProviderError as exc:
        logger.warning("get_company_overview(%s) failed: %s", ticker, exc)
        return {"ticker": ticker.upper(), "error": str(exc)}


def get_key_financials(ticker: str) -> Dict[str, Any]:
    """Core metrics only: revenue, net income, EPS, market cap, PE, cash flow."""
    try:
        return get_financial_service().get_metrics(ticker).model_dump()
    except DataProviderError as exc:
        logger.warning("get_key_financials(%s) failed: %s", ticker, exc)
        return {"ticker": ticker.upper(), "error": str(exc)}
