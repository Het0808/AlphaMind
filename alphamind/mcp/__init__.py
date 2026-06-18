"""AlphaMind Model Context Protocol (MCP) integration.

Connects the agents to external MCP servers — Filesystem, GitHub, Browser and a
local Financial Data server — and lets them dynamically discover and call the
tools each server exposes.

Components:
  • specs/auth   — declarative server specs + an authentication layer
  • MCPManager   — connects to servers and discovers their tools at runtime
  • ToolRegistry — a live catalog of discovered tools (namespaced, searchable)

Heavy deps (langchain-mcp-adapters / langgraph / mcp) are imported lazily, so
importing this package — and the rest of AlphaMind — never requires them.
"""

from .exceptions import (
    MCPAuthError,
    MCPConnectionError,
    MCPError,
    MCPToolError,
    MCPToolNotFound,
)
from .manager import MCPManager
from .registry import ToolRegistry
from .schemas import MCPServerSpec, ToolInfo, Transport

__all__ = [
    "MCPManager",
    "ToolRegistry",
    "MCPServerSpec",
    "ToolInfo",
    "Transport",
    "MCPError",
    "MCPConnectionError",
    "MCPAuthError",
    "MCPToolError",
    "MCPToolNotFound",
]
