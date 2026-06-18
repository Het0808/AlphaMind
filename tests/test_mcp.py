"""Offline tests for the MCP layer.

Exercise the registry, auth layer, server specs and the manager's dynamic-
discovery / failure-isolation logic using fake tools and an injected async loader
— no Node, no real MCP servers, no network.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional

import pytest

from alphamind.config import Settings
from alphamind.mcp.auth import is_authorized, resolve_auth
from alphamind.mcp.exceptions import MCPAuthError, MCPToolNotFound
from alphamind.mcp.manager import MCPManager
from alphamind.mcp.registry import ToolRegistry
from alphamind.mcp.schemas import MCPServerSpec
from alphamind.mcp.specs import default_server_specs


@dataclass
class FakeTool:
    name: str
    description: str = "a fake tool"
    args: dict = field(default_factory=dict)


# ── Registry ───────────────────────────────────────────────────────────────
def test_registry_namespacing_and_lookup():
    reg = ToolRegistry()
    reg.register_server("github", [FakeTool("search_repos"), FakeTool("create_issue")])
    reg.register_server("filesystem", [FakeTool("read_file")])

    assert len(reg) == 3
    assert set(reg.servers()) == {"github", "filesystem"}
    assert "github.search_repos" in reg.names()
    # bare-name lookup resolves when unique; qualified always works
    assert reg.get("read_file").name == "read_file"
    assert reg.get("github.create_issue").name == "create_issue"


def test_registry_unknown_tool_raises():
    reg = ToolRegistry()
    with pytest.raises(MCPToolNotFound):
        reg.get("nope")


def test_registry_search_and_failures():
    reg = ToolRegistry()
    reg.register_server("financial", [FakeTool("financial_snapshot", "real fundamentals")])
    reg.record_failure("browser", RuntimeError("npx not found"))
    assert reg.search("fundamentals")[0].name == "financial_snapshot"
    assert "browser" in reg.failures and "npx" in reg.failures["browser"]


# ── Auth layer ─────────────────────────────────────────────────────────────
def test_auth_missing_credential_raises():
    spec = MCPServerSpec(name="github", required_auth=["GITHUB_PERSONAL_ACCESS_TOKEN"])
    with pytest.raises(MCPAuthError):
        resolve_auth(spec, environ={})
    assert is_authorized(spec, environ={}) is False


def test_auth_injects_credential_from_environ():
    spec = MCPServerSpec(name="github", required_auth=["GITHUB_PERSONAL_ACCESS_TOKEN"])
    resolve_auth(spec, environ={"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_secret"})
    assert spec.env["GITHUB_PERSONAL_ACCESS_TOKEN"] == "ghp_secret"
    assert spec.redacted()["env"]["GITHUB_PERSONAL_ACCESS_TOKEN"] == "***"  # never leaked


# ── Server specs ───────────────────────────────────────────────────────────
def test_default_specs_cover_all_four():
    specs = {s.name: s for s in default_server_specs(Settings(github_token="ghp_x"))}
    assert set(specs) == {"filesystem", "github", "browser", "financial"}
    assert "@modelcontextprotocol/server-filesystem" in specs["filesystem"].args
    assert specs["github"].required_auth == ["GITHUB_PERSONAL_ACCESS_TOKEN"]
    assert specs["github"].env["GITHUB_PERSONAL_ACCESS_TOKEN"] == "ghp_x"
    assert specs["financial"].args == ["-m", "alphamind.mcp.servers.financial_server"]


def test_specs_can_be_disabled():
    specs = default_server_specs(Settings(mcp_enable_browser=False, mcp_enable_github=False))
    assert {s.name for s in specs} == {"filesystem", "financial"}


def test_stdio_connection_dict():
    spec = MCPServerSpec(name="fs", command="npx", args=["-y", "pkg"], env={"K": "v"})
    conn = spec.to_connection()
    assert conn == {"transport": "stdio", "command": "npx", "args": ["-y", "pkg"], "env": {"K": "v"}}


# ── Manager: dynamic discovery + failure isolation ─────────────────────────
def test_manager_discovers_and_isolates_failures():
    good = MCPServerSpec(name="filesystem", command="x")
    bad = MCPServerSpec(name="browser", command="x")

    async def loader(spec):
        if spec.name == "browser":
            raise RuntimeError("server crashed")
        return [FakeTool("read_file"), FakeTool("write_file")]

    manager = MCPManager(specs=[good, bad], loader=loader)
    registry = asyncio.run(manager.connect())

    assert manager.connected
    assert len(registry) == 2                       # only the good server's tools
    assert registry.servers() == ["filesystem"]
    assert "browser" in registry.failures           # failure recorded, not raised
    status = manager.status()
    assert status["tool_count"] == 2 and "browser" in status["failures"]


def test_manager_strict_reraises():
    bad = MCPServerSpec(name="github", command="x", required_auth=["GITHUB_PERSONAL_ACCESS_TOKEN"])

    async def loader(spec):  # never reached — auth fails first
        return []

    manager = MCPManager(specs=[bad], loader=loader)
    with pytest.raises(MCPAuthError):
        asyncio.run(manager.connect(strict=True))
