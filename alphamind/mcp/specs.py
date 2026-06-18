"""Built-in MCP server specifications for the four required integrations.

  1. Filesystem — @modelcontextprotocol/server-filesystem (stdio, no auth)
  2. GitHub     — @modelcontextprotocol/server-github (stdio, PAT required)
  3. Browser    — headless browser automation (stdio, no auth)
  4. Financial  — AlphaMind's own MCP server over the FinancialDataService (stdio)

All are toggleable via settings; commands/packages are configurable so you can
swap in alternative servers without code changes.
"""

from __future__ import annotations

import sys
from typing import List

from ..config import get_settings
from .schemas import MCPServerSpec, Transport

_GITHUB_PAT = "GITHUB_PERSONAL_ACCESS_TOKEN"


def default_server_specs(settings=None) -> List[MCPServerSpec]:
    settings = settings or get_settings()
    specs: List[MCPServerSpec] = []

    if settings.mcp_enable_filesystem:
        specs.append(MCPServerSpec(
            name="filesystem",
            description="Read/write files under a sandboxed root directory.",
            command=settings.npx_command,
            args=["-y", "@modelcontextprotocol/server-filesystem", settings.mcp_filesystem_root],
        ))

    if settings.mcp_enable_github:
        specs.append(MCPServerSpec(
            name="github",
            description="Search repos, read files, manage issues and pull requests.",
            command=settings.npx_command,
            args=["-y", "@modelcontextprotocol/server-github"],
            env={_GITHUB_PAT: settings.github_token} if settings.github_token else {},
            required_auth=[_GITHUB_PAT],
        ))

    if settings.mcp_enable_browser:
        specs.append(MCPServerSpec(
            name="browser",
            description="Navigate pages and extract content via a headless browser.",
            command=settings.npx_command,
            args=["-y", settings.mcp_browser_package],
        ))

    if settings.mcp_enable_financial:
        specs.append(MCPServerSpec(
            name="financial",
            description="AlphaMind financial data (Yahoo + SEC EDGAR + FMP).",
            transport=Transport.STDIO,
            command=sys.executable,
            args=["-m", "alphamind.mcp.servers.financial_server"],
        ))

    return specs
