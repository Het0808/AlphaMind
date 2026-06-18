"""MCPManager — connects to MCP servers and dynamically discovers their tools.

For each enabled, authorized server it loads the tool list at runtime and registers
it. Per-server failures are isolated (recorded in the registry, not raised) unless
`strict=True`, so one broken server never takes down the others.

The default tool loader uses `langchain-mcp-adapters` and is imported lazily; an
alternative loader can be injected (used by tests) to exercise the manager without
spawning real servers.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, List, Optional

from ..config import get_settings
from .auth import resolve_auth
from .exceptions import MCPError
from .registry import ToolRegistry
from .schemas import MCPServerSpec
from .specs import default_server_specs

logger = logging.getLogger(__name__)

ToolLoader = Callable[[MCPServerSpec], Awaitable[List[object]]]


class MCPManager:
    def __init__(
        self,
        specs: Optional[List[MCPServerSpec]] = None,
        *,
        settings=None,
        loader: Optional[ToolLoader] = None,
        registry: Optional[ToolRegistry] = None,
    ):
        self.settings = settings or get_settings()
        self.specs = specs if specs is not None else default_server_specs(self.settings)
        self.registry = registry or ToolRegistry()
        self._loader = loader
        self.connected = False

    async def _default_loader(self, spec: MCPServerSpec) -> List[object]:
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except ImportError as exc:  # pragma: no cover
            raise MCPError("langchain-mcp-adapters is not installed", server=spec.name) from exc

        client = MultiServerMCPClient({spec.name: spec.to_connection()})
        try:
            return await client.get_tools(server_name=spec.name)
        except Exception as exc:  # noqa: BLE001
            raise MCPError(f"failed to load tools: {exc}", server=spec.name) from exc

    async def connect(self, *, strict: bool = False) -> ToolRegistry:
        """Connect to every enabled server and discover its tools."""
        loader = self._loader or self._default_loader
        for spec in self.specs:
            if not spec.enabled:
                continue
            try:
                resolve_auth(spec)  # raises MCPAuthError if a credential is missing
                tools = await loader(spec)
                self.registry.register_server(spec.name, tools)
            except Exception as exc:  # noqa: BLE001 - isolate per-server failures
                logger.warning("MCP server '%s' unavailable: %s", spec.name, exc)
                self.registry.record_failure(spec.name, exc)
                if strict:
                    raise
        self.connected = True
        logger.info(
            "MCP connected: %d tools across %s (failed: %s)",
            len(self.registry), self.registry.servers(), list(self.registry.failures),
        )
        return self.registry

    def connect_sync(self, *, strict: bool = False) -> ToolRegistry:
        return asyncio.run(self.connect(strict=strict))

    # ── accessors ──────────────────────────────────────────────────────
    def get_tools(self, server: Optional[str] = None, names: Optional[List[str]] = None) -> List[object]:
        return self.registry.langchain_tools(server=server, names=names)

    def status(self) -> dict:
        return {
            "connected": self.connected,
            "servers": self.registry.servers(),
            "tool_count": len(self.registry),
            "tools": [i.qualified_name for i in self.registry.list_infos()],
            "failures": self.registry.failures,
        }
