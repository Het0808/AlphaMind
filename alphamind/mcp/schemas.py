"""Declarative MCP server + tool descriptors.

`MCPServerSpec` is transport-agnostic and converts to the connection dict expected
by `langchain-mcp-adapters`. `ToolInfo` is the registry's record of a discovered
tool, including its (namespaced) name and JSON input schema.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Transport(str, Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "streamable_http"


class MCPServerSpec(BaseModel):
    name: str
    transport: Transport = Transport.STDIO
    description: str = ""
    enabled: bool = True

    # stdio transport
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)

    # http/sse transport
    url: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)

    # names of env vars that MUST be present for this server to start
    required_auth: List[str] = Field(default_factory=list)

    def to_connection(self) -> Dict[str, Any]:
        """Render the connection dict consumed by MultiServerMCPClient."""
        if self.transport == Transport.STDIO:
            conn: Dict[str, Any] = {"transport": "stdio", "command": self.command, "args": self.args}
            if self.env:
                conn["env"] = self.env
            return conn
        conn = {"transport": self.transport.value, "url": self.url}
        if self.headers:
            conn["headers"] = self.headers
        return conn

    def redacted(self) -> Dict[str, Any]:
        """A log/response-safe view with secrets masked."""
        data = self.model_dump()
        data["env"] = {k: "***" for k in self.env}
        data["headers"] = {k: "***" for k in self.headers}
        return data


class ToolInfo(BaseModel):
    name: str
    server: str
    description: str = ""
    input_schema: Dict[str, Any] = Field(default_factory=dict)

    @property
    def qualified_name(self) -> str:
        return f"{self.server}.{self.name}"
