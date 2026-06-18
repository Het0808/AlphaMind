"""MCP-powered agent.

A LangGraph ReAct agent bound to *whatever* tools the MCP servers expose at
runtime — it discovers tools dynamically via the MCPManager and decides which to
call. This is the concrete demonstration of "agents dynamically discover and use
tools": no tool is hard-coded.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from ..llm import get_llm
from .manager import MCPManager

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are AlphaMind's MCP agent. You have access to tools discovered from "
    "external MCP servers (filesystem, GitHub, browser, financial data). Inspect "
    "the available tools, pick the right ones, and call them to fulfill the "
    "request. Prefer the financial tools for company fundamentals. If no tool "
    "fits, answer directly and say so."
)


async def build_mcp_agent(manager: Optional[MCPManager] = None):
    """Connect to MCP servers and build a ReAct agent over the discovered tools."""
    manager = manager or MCPManager()
    if not manager.connected:
        await manager.connect()

    from langgraph.prebuilt import create_react_agent

    tools = manager.get_tools()
    agent = create_react_agent(get_llm(), tools, prompt=_SYSTEM)
    return agent, manager


async def run_mcp_agent(query: str, *, manager: Optional[MCPManager] = None) -> str:
    agent, _ = await build_mcp_agent(manager)
    result = await agent.ainvoke({"messages": [("user", query)]})
    return result["messages"][-1].content


def run_mcp_agent_sync(query: str) -> str:
    return asyncio.run(run_mcp_agent(query))
