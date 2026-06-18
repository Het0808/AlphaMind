"""Tool registry — a live catalog of tools discovered across MCP servers.

Tools are namespaced by server (`github.search_repositories`) to avoid collisions,
looked up by qualified or bare name, and searchable. Per-server connection
failures are recorded so callers can see what's unavailable and why.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .exceptions import MCPToolNotFound
from .schemas import ToolInfo

logger = logging.getLogger(__name__)


def _extract_schema(tool: Any) -> Dict[str, Any]:
    """Best-effort JSON schema for a LangChain/MCP tool's inputs."""
    args = getattr(tool, "args", None)
    if isinstance(args, dict):
        return args
    schema_cls = getattr(tool, "args_schema", None)
    if schema_cls is not None:
        for attr in ("model_json_schema", "schema"):
            fn = getattr(schema_cls, attr, None)
            if callable(fn):
                try:
                    return fn()
                except Exception:  # noqa: BLE001
                    return {}
    return {}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Any] = {}          # qualified_name -> tool object
        self._infos: Dict[str, ToolInfo] = {}     # qualified_name -> ToolInfo
        self._by_server: Dict[str, List[str]] = {}
        self.failures: Dict[str, str] = {}        # server -> error message

    # ── population (dynamic discovery) ─────────────────────────────────
    def register_server(self, server: str, tools: List[Any]) -> List[ToolInfo]:
        registered: List[ToolInfo] = []
        for tool in tools:
            info = ToolInfo(
                name=getattr(tool, "name", str(tool)),
                server=server,
                description=getattr(tool, "description", "") or "",
                input_schema=_extract_schema(tool),
            )
            qn = info.qualified_name
            self._tools[qn] = tool
            self._infos[qn] = info
            self._by_server.setdefault(server, []).append(qn)
            registered.append(info)
        logger.info("Registered %d tools from MCP server '%s'", len(registered), server)
        return registered

    def record_failure(self, server: str, error: Any) -> None:
        self.failures[server] = str(error)

    # ── lookup ─────────────────────────────────────────────────────────
    def get(self, name: str) -> Any:
        if name in self._tools:
            return self._tools[name]
        matches = [qn for qn in self._tools if qn.split(".", 1)[1] == name]
        if len(matches) == 1:
            return self._tools[matches[0]]
        if not matches:
            raise MCPToolNotFound(f"tool '{name}' not found")
        raise MCPToolNotFound(f"tool '{name}' is ambiguous across servers: {matches}")

    def list_infos(self, server: Optional[str] = None) -> List[ToolInfo]:
        infos = self._infos.values()
        return [i for i in infos if server is None or i.server == server]

    def langchain_tools(self, server: Optional[str] = None, names: Optional[List[str]] = None) -> List[Any]:
        """Return the underlying tool objects to bind to an agent."""
        out = []
        for qn, tool in self._tools.items():
            info = self._infos[qn]
            if server is not None and info.server != server:
                continue
            if names is not None and info.name not in names and qn not in names:
                continue
            out.append(tool)
        return out

    def search(self, query: str) -> List[ToolInfo]:
        q = query.lower()
        return [i for i in self._infos.values() if q in i.name.lower() or q in i.description.lower() or q in i.server.lower()]

    # ── introspection ──────────────────────────────────────────────────
    def servers(self) -> List[str]:
        return list(self._by_server.keys())

    def names(self) -> List[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)
