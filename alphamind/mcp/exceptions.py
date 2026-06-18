"""Typed errors for the MCP layer so failures can be handled precisely."""

from __future__ import annotations


class MCPError(Exception):
    """Base class for all MCP failures."""

    def __init__(self, message: str, *, server: str | None = None):
        self.server = server
        super().__init__(f"[{server or 'mcp'}] {message}")


class MCPConnectionError(MCPError):
    """Could not start/connect to an MCP server (transport/process failure)."""


class MCPAuthError(MCPError):
    """A server is missing required credentials."""


class MCPToolError(MCPError):
    """A discovered tool failed during invocation."""


class MCPToolNotFound(MCPError):
    """Requested tool is not present in the registry."""


class MCPServerNotFound(MCPError):
    """Requested server is not configured."""
