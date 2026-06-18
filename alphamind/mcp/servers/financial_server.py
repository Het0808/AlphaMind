"""AlphaMind Financial Data MCP server.

Exposes the existing multi-source FinancialDataService (Yahoo + SEC EDGAR + FMP)
as MCP tools, so any MCP client — including AlphaMind's own MCP agent — can pull
real fundamentals for a ticker. Run over stdio:

    python -m alphamind.mcp.servers.financial_server
"""

from __future__ import annotations

from typing import Any, Dict

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise SystemExit("The 'mcp' package is required: pip install mcp") from exc

from alphamind.tools import (
    get_company_overview,
    get_financial_snapshot,
    get_key_financials,
)

mcp = FastMCP("alphamind-financial")


@mcp.tool()
def company_overview(ticker: str) -> Dict[str, Any]:
    """Company overview: name, sector, industry, description, exchange, employees."""
    return get_company_overview(ticker)


@mcp.tool()
def financial_metrics(ticker: str) -> Dict[str, Any]:
    """Core metrics: revenue, net income, EPS, market cap, P/E, cash flow."""
    return get_key_financials(ticker)


@mcp.tool()
def financial_snapshot(ticker: str) -> Dict[str, Any]:
    """Full snapshot: overview + metrics + provenance (which source gave each field)."""
    return get_financial_snapshot(ticker)


if __name__ == "__main__":
    mcp.run()
